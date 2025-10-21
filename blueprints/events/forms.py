"""Forms for event submission."""
from wtforms import Form, StringField, DateField, URLField, EmailField, validators


class EventForm(Form):
    """Form for individual event."""
    title = StringField('Event Title', [
        validators.DataRequired(), 
        validators.Length(min=3, max=200)
    ])
    date = DateField('Date', [validators.DataRequired()])
    end_date = DateField('End Date', [validators.Optional()])
    time = StringField('Time', [validators.DataRequired()])
    url = URLField('Event URL', [validators.DataRequired(), validators.URL()])
    location = StringField('Location')
    cost = StringField('Cost')


class EventSubmissionForm(Form):
    """Form for event submission with user info."""
    submitted_by = StringField('Your Name', [validators.Length(min=2)])
    submitter_link = URLField('Your Website/Social Media Link', [
        validators.Optional(), 
        validators.URL()
    ])
    email = EmailField('Your Email', [
        validators.DataRequired(), 
        validators.Email()
    ])


class MeetupGroupForm(Form):
    """Form for meetup group."""
    name = StringField('Group Name', [
        validators.DataRequired(), 
        validators.Length(min=2, max=200)
    ])
    url = URLField('Group URL', [validators.DataRequired(), validators.URL()])


class MeetupSubmissionForm(Form):
    """Form for meetup group submission with user info."""
    submitted_by = StringField('Your Name', [validators.Length(min=2)])
    submitter_link = URLField('Your Website/Social Media Link', [
        validators.Optional(), 
        validators.URL()
    ])
    email = EmailField('Your Email', [
        validators.DataRequired(), 
        validators.Email()
    ])


class ICalGroupForm(Form):
    """Form for iCal feed group."""
    name = StringField('Group Name', [
        validators.DataRequired(), 
        validators.Length(min=2, max=200)
    ])
    url = URLField('Group URL', [validators.DataRequired(), validators.URL()])
    ical = URLField('iCal Feed URL', [validators.DataRequired(), validators.URL()])
    fallback_url = URLField('Fallback URL', [validators.Optional(), validators.URL()])
    submitted_by = StringField('Your Name', [validators.Length(min=2)])
    submitter_link = URLField('Your Website/Social Media Link', [
        validators.Optional(), 
        validators.URL()
    ])
    email = EmailField('Your Email', [
        validators.DataRequired(), 
        validators.Email()
    ])
