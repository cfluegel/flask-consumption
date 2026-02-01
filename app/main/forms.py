from flask_wtf import FlaskForm
from wtforms import DateField, FloatField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, ValidationError


class GermanFloatField(FloatField):
    """FloatField that accepts German decimal format (comma as separator)."""

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                # Replace comma with dot for parsing
                value_str = valuelist[0].replace(',', '.')
                self.data = float(value_str)
            except ValueError:
                self.data = None
                raise ValidationError('Ungültige Zahl')


class LoginForm(FlaskForm):
    username = StringField('Benutzername', validators=[DataRequired()])
    password = PasswordField('Passwort', validators=[DataRequired()])
    submit = SubmitField('Anmelden')


class ReadingForm(FlaskForm):
    meter_id = SelectField('Zähler', coerce=int, validators=[DataRequired()])
    reading_date = DateField('Datum', validators=[DataRequired()])
    value = GermanFloatField('Neuer Zählerstand', validators=[DataRequired()])
    submit = SubmitField('Speichern')
