from mongoengine import Document, EmbeddedDocument
from mongoengine import StringField, DateTimeField, IntField, BooleanField
from mongoengine import ListField, EmbeddedDocumentField
from flask.ext.babel import gettext as _
import datetime

class MenuLink(EmbeddedDocument):
    text = StringField(required=True)
    link = StringField(required=True)

class Menu(Document):
    site = StringField(required=True)
    links = ListField(EmbeddedDocumentField(MenuLink))
    simple = BooleanField(default=False)
    background_color = StringField()
    hover_background_color = StringField()
    text_color = StringField()
    hover_text_color = StringField()
    active_background_color = StringField()
    active_text_color = StringField()

class LoginToken(Document):
    site = StringField(required=True)
    code = StringField(required=True)
    created = DateTimeField(default=datetime.datetime.now)

class Site(Document):
    domain = StringField(required=True)
    owner_email = StringField()  # Will get deprecated when user models arrive
    verified_email = BooleanField(default=False)
    name = StringField(required=True)
    description = StringField()
    header_image = StringField()
    footers = ListField(StringField())
    active_modules = ListField(StringField())
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
        return site


class File(Document):
    site = StringField(required=True)
    name = StringField(required=True)
    slug = StringField(required=True)
    content_type = StringField()
    content_length = IntField()
    created = DateTimeField(default=datetime.datetime.now)

    meta = {
            'ordering': ['-created']
            }

class Page(Document):
    site = StringField(required=True)
    name = StringField(required=True)
    slug = StringField(required=True)
    content = StringField()
    created = DateTimeField(default=datetime.datetime.now)

    meta = {
            'ordering': ['-created']
            }

    def __unicode__(self):
        return self.name

class Slide(EmbeddedDocument):
    text = StringField()
    image_url = StringField()
    caption = StringField()
    caption_link = StringField()

class Job(Document):
    site = StringField(required=True)
    name = StringField(required=True)
    slug = StringField(required=True)
    intro = StringField()
    description = StringField()
    slides = ListField(EmbeddedDocumentField(Slide))
    categories = ListField(StringField())
    created = DateTimeField(default=datetime.datetime.now)

    meta = {
            'ordering': ['-created']
            }

    def __unicode__(self):
        return self.name

class Portfolio(Document):
    site = StringField(required=True)
    active = BooleanField(default=False)
    title = StringField()
    intro = StringField()
    categories = ListField(StringField())

    def __unicode__(self):
        if self.title:
            return self.title
        else:
            return _("Portfolio")

    @property
    def all_jobs(self):
        return Job.objects.filter(site=self.site)

class Blog(Document):
    site = StringField(required=True)
    active = BooleanField(default=False)
    title = StringField()

    def __unicode__(self):
        if self.title:
            return self.title
        else:
            return _("Blog")

    @property
    def all_posts(self):
        return Post.objects.filter(site=self.site)

class Post(Document):
    site = StringField(required=True)
    name = StringField(required=True)
    slug = StringField(required=True)
    created = DateTimeField()
    year = IntField()
    month = IntField()
    day = IntField()
    text = StringField()
    image_slug = StringField()

    meta = {
            'ordering': ['-created']
            }

    def __unicode__(self):
        return self.name

class Person(Document):
    site = StringField(required=True)
    name = StringField(required=True)
    slug = StringField(required=True)
    title = StringField()
    phone = StringField()
    email = StringField()
    twitter = StringField()
    facebook = StringField()
    linkedin = StringField()
    description = StringField()
    image_slug = StringField()

    def __unicode__(self):
        return self.name

class Personnel(Document):
    site = StringField(required=True)
    title = StringField()
    subtitle = StringField()
    people = ListField(StringField())
    effect = StringField()
    per_line = IntField(default=4)

    def __unicode__(self):
        if self.title:
            return self.title
        else:
            return _("Personnel")
