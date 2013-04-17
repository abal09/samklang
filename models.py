from mongoengine import Document
from mongoengine import StringField, DateTimeField, IntField, ListField, BooleanField
import datetime

class Site(Document):
    domain = StringField(required=True)
    owner_email = StringField()  # Will get deprecated when user models arrive
    verified_email = BooleanField(default=False)
    name = StringField(required=True)
    description = StringField()
    header_image = StringField()
    footers = ListField(StringField())
    created = DateTimeField(default=datetime.datetime.now)

    meta = {
            'ordering': ['-created']
            }

    def __unicode__(self):
        return self.domain

    @classmethod
    def get_by_hostname(cls, hostname, domain_root):
        host = hostname.split(":")[0]
        if host.endswith("." + domain_root):
            strip_length = len(domain_root) + 1
            host = host[:-strip_length]
        site = cls.objects(domain=host).first()
        if not site:
            site = cls.objects.first()
        return site


class File(Document):
    name = StringField(required=True)
    slug = StringField(required=True)
    content_type = StringField()
    content_length = IntField()
    created = DateTimeField(default=datetime.datetime.now)

    meta = {
            'ordering': ['-created']
            }
