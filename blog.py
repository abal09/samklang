from flask import Blueprint, render_template, abort, request, g, redirect, url_for, current_app
from models import Blog, Post, File
from utils import save_file, slugify

blog = Blueprint('blog', __name__, template_folder='templates/blog', url_prefix='/b')

@blog.route("/")
def show_blog():
    try:
        if not "blog" in g.site.active_modules:
            raise(Blog.DoesNotExist)
        b, created = Blog.objects.get_or_create(site=g.site.domain)
    except Blog.DoesNotExist:
        abort(404)
    return render_template("blog.html", blog=b)

@blog.route("/e", methods=["POST", "GET"])
def edit_blog():
    if not g.site.domain == g.user:
        abort(403)
    b, created = Blog.objects.get_or_create(site=g.site.domain)

    if request.method == "POST":
        b.title = request.form.get("title")
        b.save()
        return redirect(url_for(".show_blog"))

    return render_template("edit_blog.html", blog=b)

@blog.route("/<int:year>/<int:month>/<int:day>/<slug>")
def post(year, month, day, slug):
    p = Post.objects.get(site=g.site.domain, year=year, month=month, day=day, slug=slug)
    return render_template("post.html", post=p)

@blog.route("/n", methods=["POST", "GET"])
def new_post():
    if not g.site.domain == g.user:
        abort(403)

    p = Post()
    if request.method == "POST":
        reqfile = request.files.get('file')
        if reqfile:
            f = File()
            f.site = g.site.domain
            f.name = reqfile.filename
            f.content_type = reqfile.mimetype
            f.slug, f.content_length = save_file(reqfile, blog.config["UPLOAD_FOLDER"])
            f.save()

        import datetime
        p.site = g.site.domain
        p.name = request.form.get("name")
        p.created = datetime.datetime.utcnow()
        p.year = p.created.year
        p.month = p.created.month
        p.day = p.created.day
        slugs = [__j.slug for __j in Post.objects.filter(site=g.site.domain, year=p.year, month=p.month, day=p.day, slug=p.slug)]
        counter = 1
        slug = slugify(p.name)
        __slug = slug
        while __slug in slugs:
            counter += 1
            __slug = "%s_%d" % (slug, counter)
        p.slug = __slug
        p.text = request.form.get("text")
        if reqfile:
            p.image_slug = f.slug
        p.save()
        return redirect(url_for("post", year=p.year, month=p.month, day=p.day, slug=p.slug))
    return render_template("edit_post.html", post=p)

@blog.route("/<int:year>/<int:month>/<int:day>/<slug>/e", methods=["POST", "GET"])
def edit_post(year, month, day, slug):
    try:
        p = Post.objects.get(site=g.site.domain, year=year, month=month, day=day, slug=slug)
    except Post.DoesNotExist:
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
            f.slug, f.content_length = save_file(reqfile, current_app.config["UPLOAD_FOLDER"])
            f.save()

        p.name = request.form.get("name")
        p.text = request.form.get("text")
        if reqfile:
            p.image_slug = f.slug
        p.save()
        return redirect(url_for("post", year=p.year, month=p.month, day=p.day, slug=p.slug))

    return render_template("edit_post.html", post=p)
