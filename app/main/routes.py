from datetime import date

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import main_bp
from .forms import LoginForm, ReadingForm
from ..extensions import db
from ..models import Meter, MeterReading, User


@main_bp.route('/')
def index():
    meters = Meter.query.all()
    consumption_data = {m.id: m.get_monthly_consumption() for m in meters}
    avg_3month = {m.id: m.get_3month_average() for m in meters}
    pred_weighted = {m.id: m.get_prediction_weighted() for m in meters}
    pred_seasonal = {m.id: m.get_prediction_seasonal() for m in meters}
    yearly_consumption = {m.id: m.get_yearly_consumption() for m in meters}
    return render_template('index.html', meters=meters, consumption_data=consumption_data,
                           avg_3month=avg_3month, pred_weighted=pred_weighted,
                           pred_seasonal=pred_seasonal, yearly_consumption=yearly_consumption)


@main_bp.route('/graphs')
def graphs():
    meters = Meter.query.all()
    consumption_data = {m.id: m.get_monthly_consumption(months=12, newest_first=False) for m in meters}
    return render_template('graphs.html', meters=meters, consumption_data=consumption_data)


@main_bp.route('/graph/<int:meter_id>')
def graph_detail(meter_id):
    meter = Meter.query.get_or_404(meter_id)
    consumption_data = meter.get_monthly_consumption(months=None, newest_first=False)
    return render_template('graph_detail.html', meter=meter, consumption_data=consumption_data)


@main_bp.route('/meter/<int:meter_id>')
def meter_detail(meter_id):
    meter = Meter.query.get_or_404(meter_id)
    readings = meter.readings.all()
    return render_template('meter_detail.html', meter=meter, readings=readings)


@main_bp.route('/reading/new', methods=['GET', 'POST'])
def reading_new():
    form = ReadingForm()
    form.meter_id.choices = [(m.id, f"{m.name} ({m.unit})") for m in Meter.query.all()]

    # Pre-fill with today's date and meter_id from query params
    selected_meter = None
    previous_reading = None
    if request.method == 'GET':
        form.reading_date.data = date.today()
        meter_id = request.args.get('meter_id', type=int)
        if meter_id:
            form.meter_id.data = meter_id
            selected_meter = Meter.query.get(meter_id)
            if selected_meter:
                previous_reading = selected_meter.get_previous_reading()

    if form.validate_on_submit():
        reading = MeterReading(
            meter_id=form.meter_id.data,
            reading_date=form.reading_date.data,
            value=form.value.data
        )
        db.session.add(reading)
        db.session.commit()
        flash('Ablesung erfolgreich gespeichert.', 'success')
        return redirect(url_for('main.meter_detail', meter_id=form.meter_id.data))

    return render_template('reading_form.html', form=form, title='Neue Ablesung',
                           previous_reading=previous_reading, selected_meter=selected_meter)


@main_bp.route('/reading/<int:reading_id>/edit', methods=['GET', 'POST'])
def reading_edit(reading_id):
    reading = MeterReading.query.get_or_404(reading_id)
    form = ReadingForm(obj=reading)
    form.meter_id.choices = [(m.id, f"{m.name} ({m.unit})") for m in Meter.query.all()]

    # Get the reading before the one being edited
    selected_meter = reading.meter
    previous_reading = selected_meter.get_previous_reading(before_date=reading.reading_date)

    if form.validate_on_submit():
        reading.meter_id = form.meter_id.data
        reading.reading_date = form.reading_date.data
        reading.value = form.value.data
        db.session.commit()
        flash('Ablesung erfolgreich aktualisiert.', 'success')
        return redirect(url_for('main.meter_detail', meter_id=reading.meter_id))

    return render_template('reading_form.html', form=form, title='Ablesung bearbeiten',
                           previous_reading=previous_reading, selected_meter=selected_meter)


@main_bp.route('/reading/<int:reading_id>/delete', methods=['POST'])
def reading_delete(reading_id):
    reading = MeterReading.query.get_or_404(reading_id)
    meter_id = reading.meter_id
    db.session.delete(reading)
    db.session.commit()
    flash('Ablesung erfolgreich gelöscht.', 'success')
    return redirect(url_for('main.meter_detail', meter_id=meter_id))

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Erfolgreich angemeldet.', 'success')
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.index')
            return redirect(next_page)
        flash('Ungültige Anmeldedaten.', 'danger')

    return render_template('login.html', form=form)

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Du wurdest abgemeldet.', 'info')
    return redirect(url_for('main.index'))
