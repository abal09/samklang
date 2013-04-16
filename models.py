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

    @classmethod
    def get_by_hostname(cls, hostname):
        from config import ROOT_DOMAIN

        host = hostname.split(":")[0]
        if host.endswith("." + ROOT_DOMAIN):
            strip_length = len(ROOT_DOMAIN) + 1
            host = host[:-strip_length]
        site = cls.objects(domain=host).first()
        if not site:
            #flash("%s not found" % host)
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
