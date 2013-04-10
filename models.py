from mongoengine import Document, StringField, DateTimeField
import datetime

class Site(Document):
    domain = StringField(required=True)
    name = StringField(required=True)
    description = StringField()
    created = DateTimeField(default=datetime.datetime.now)
