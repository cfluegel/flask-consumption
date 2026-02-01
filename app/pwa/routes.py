from flask import render_template

from . import pwa_bp


@pwa_bp.route('/')
def index():
    """PWA dashboard - meter list with latest readings."""
    return render_template('pwa_index.html')


@pwa_bp.route('/setup')
def setup():
    """API key entry page (one-time setup)."""
    return render_template('pwa_setup.html')


@pwa_bp.route('/meter/<int:meter_id>')
def meter_detail(meter_id):
    """Meter detail with readings history."""
    return render_template('pwa_meter.html', meter_id=meter_id)


@pwa_bp.route('/meter/<int:meter_id>/add')
def add_reading(meter_id):
    """Add reading form."""
    return render_template('pwa_reading_form.html', meter_id=meter_id)


@pwa_bp.route('/manifest.json')
def manifest():
    """Web App Manifest."""
    return pwa_bp.send_static_file('manifest.json')
