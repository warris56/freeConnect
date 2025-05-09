from flask_wtf import FlaskForm
from wtforms import TextAreaField, FileField, StringField, DateField
from wtforms.validators import Length, Optional, URL
from flask_wtf.file import FileAllowed

class ProfileUpdateForm(FlaskForm):
    bio = TextAreaField('Bio', validators=[Length(max=500)])
    profile_picture = FileField('Profile Picture', validators=[
        FileAllowed(['jpg', 'png'], 'Images only!')
    ])
    
    # New fields
    full_name = StringField("Full Name", validators=[Optional()])
    location = StringField("Location", validators=[Optional()])
    website = StringField("Website", validators=[Optional(), URL()])
    birthdate = DateField("Birthdate", format='%Y-%m-%d', validators=[Optional()])
