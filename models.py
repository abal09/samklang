from mongoengine import Document, StringField, DateTimeField, IntField
import datetime

class Site(Document):
    domain = StringField(required=True)
    name = StringField(required=True)
    description = StringField()
    created = DateTimeField(default=datetime.datetime.now)

class File(Document):
    name = StringField(required=True)
    slug = StringField(required=True)
    content_type = StringField()
    content_length = IntField()
    created = DateTimeField(default=datetime.datetime.now)

    meta = {
            'ordering': ['-created']
            }
