from flask import Blueprint, render_template, abort, request, g, redirect, url_for
from models import Page
from utils import slugify

pages = Blueprint('pages', __name__, template_folder='templates/pages')

@pages.route("/pages/", methods=["POST", "GET"])
def show_pages():
    if request.method == "POST" and g.site.domain == g.user:
        name = request.form['name']
        if name:
            p = Page()
            p.name = name
            p.slug = slugify(name)
            p.site = g.site.domain
            p.save()
            return redirect(url_for(".edit_page", slug=p.slug))
    pages = Page.objects(site=g.site.domain)
    return render_template('pages.html', pages=pages)

@pages.route("/<slug>/")
def page(slug):
    try:
        page = Page.objects.get(slug=slug, site=g.site.domain)
    except Page.DoesNotExist:
        abort(404)
    return render_template("page.html", page=page)

@pages.route("/<slug>/e", methods=["POST", "GET"])
def edit_page(slug):
    try:
        page = Page.objects.get(slug=slug, site=g.site.domain)
    except Page.DoesNotExist:
        abort(404)

    if request.method == "POST" and g.site.domain == g.user:
        page.name = request.form["name"]
        page.content = request.form["content"]
        page.save()
        return redirect(url_for(".page", slug=page.slug))
    return render_template("edit_page.html", page=page)
