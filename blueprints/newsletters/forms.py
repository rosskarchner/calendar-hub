"""Forms for newsletter subscription."""
from wtforms import Form, EmailField, validators


class NewsletterSignupForm(Form):
    """Form for newsletter signup."""
    email = EmailField('Email', [
        validators.DataRequired(),
        validators.Email()
    ])
