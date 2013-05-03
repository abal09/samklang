from flask import Blueprint, g, render_template, abort, request, redirect, url_for, current_app
from models import Personnel, Person, File
from utils import save_file, slugify

personnel = Blueprint('personnel', __name__, template_folder='templates/personnel', url_prefix='/d')

@personnel.route("/")
def show_personnel():
    try:
        if not "personnel" in g.site.active_modules:
            raise(Personnel.DoesNotExist)
        p, created = Personnel.objects.get_or_create(site=g.site.domain)
    except Personnel.DoesNotExist:
        abort(404)

    pp = {}
    for person in Person.objects.filter(site=g.site.domain):
        pp[person.slug] = person

    people = []
    for slug in p.people:
        if slug in pp:
            people.append(pp[slug])
            del pp[slug]

    return render_template("personnel.html", personnel=p, people=people)

@personnel.route("/<slug>")
def show_person(slug):
    person = Person.objects.get(site=g.site.domain, slug=slug)
    return render_template("person.html", person=person)

@personnel.route("/e", methods=["POST", "GET"])
def edit_personnel():
    if not g.site.domain == g.user:
        abort(403)
    p, created = Personnel.objects.get_or_create(site=g.site.domain)

    pp = {}
    for person in Person.objects.filter(site=g.site.domain):
        pp[person.slug] = person

    people = []
    for slug in p.people:
        if slug in pp:
            people.append(pp[slug])
            del pp[slug]

    unrecognized_people = pp.keys()

    if request.method == "POST":
        p.people = [ slug for slug in request.form.getlist("slug") if slug ]
        p.title = request.form.get("title")
        p.subtitle = request.form.get("subtitle")
        p.per_line = request.form.get("per_line")
        p.save()
        return redirect(url_for(".show_personnel"))

    return render_template("edit_personnel.html", personnel=p, unrecognized_people=unrecognized_people)

@personnel.route("/n", methods=["POST", "GET"])
def new_person():
    if not g.site.domain == g.user:
        abort(403)

    p = Person()
    if request.method == "POST":
        reqfile = request.files.get('file')
        if reqfile:
            f = File()
            f.site = g.site.domain
            f.name = reqfile.filename
            f.content_type = reqfile.mimetype
            f.slug, f.content_length = save_file(reqfile, current_app.config["UPLOAD_FOLDER"])
            f.save()

        p.site = g.site.domain
        p.name = request.form.get("name")
        p.title = request.form.get("title")
        p.phone = request.form.get("phone")
        p.email = request.form.get("email")
        p.twitter = request.form.get("twitter")
        p.description = request.form.get("description")
        slugs = [ __p.slug for __p in Person.objects.filter(site=g.site.domain) ]
        slug = slugify(p.name)
        counter = 1
        __slug = slug
        while __slug in slugs:
            counter += 1
            __slug = "%s_%d" % (slug, counter)
        p.slug = __slug

        if reqfile:
            p.image_slug = f.slug
        p.save()

        pl = Personnel.objects.get(site=g.site.domain)
        pl.people.append(p.slug)
        pl.save()

        return redirect(url_for(".show_personnel"))
    return render_template("edit_person.html", person=p)

@personnel.route("/<slug>/e", methods=["POST", "GET"])
def edit_person(slug):
    try:
        p = Person.objects.get(site=g.site.domain, slug=slug)
    except Person.DoesNotExist:
        abort(404)

    if not g.site.domain == g.user:
        abort(403)

    if request.method == "POST":
        reqfile = request.files.get('file')
        if reqfile:
            f = File()
            f.site = g.site.domain
            f.name = reqfile.filename
            f.content_type = reqfile.mimetype
            f.slug, f.content_length = save_file(reqfile, request.config["UPLOAD_FOLDER"])
            f.save()

        p.name = request.form.get("name")
        p.title = request.form.get("title")
        p.phone = request.form.get("phone")
        p.email = request.form.get("email")
        p.twitter = request.form.get("twitter")
        p.description = request.form.get("description")
        if reqfile:
            p.image_slug = f.slug
        p.save()
        return redirect(url_for(".show_person", slug=p.slug))

    return render_template("edit_person.html", person=p)
