from flask import Blueprint, g, request, abort, render_template, redirect, url_for
from models import Portfolio, Job, Slide
from utils import slugify

portfolio = Blueprint('portfolio', __name__, template_folder='templates/portfolio', url_prefix='/p')

@portfolio.route("/")
def show_portfolio():
    try:
        if not "portfolio" in g.site.active_modules:
            raise(Portfolio.DoesNotExist)
        p = Portfolio.objects.get(site=g.site.domain)
    except Portfolio.DoesNotExist:
        abort(404)
    return render_template("portfolio.html", portfolio=p)

@portfolio.route("/e", methods=["POST", "GET"])
def edit_portfolio():
    if not g.site.domain == g.user:
        abort(403)
    try:
        p = Portfolio.objects.get(site=g.site.domain)
    except Portfolio.DoesNotExist:
        p = Portfolio.objects.create(site=g.site.domain)

    if request.method == "POST":
        p.title = request.form.get("title")
        p.intro = request.form.get("intro")
        p.categories = [ c.strip() for c in request.form.get("categories").split(",") ]
        p.save()
        return redirect(url_for(".show_portfolio"))

    return render_template("edit_portfolio.html", portfolio=p)

@portfolio.route("/<slug>")
def job(slug):
    try:
        j = Job.objects.get(site=g.site.domain, slug=slug)
    except Job.DoesNotExist:
        abort(404)
    return render_template("job.html", job=j)

@portfolio.route("/n", methods=["POST", "GET"])
def new_job():
    if not g.site.domain == g.user:
        abort(403)

    j = Job()
    if request.method == "POST":
        portfolio = Portfolio.objects.get(site=g.site.domain)
        job_name = request.form.get("name")
        slugs = [__j.slug for __j in Job.objects.filter(site=g.site.domain)]
        counter = 1
        slug = slugify(job_name)
        __slug = slug
        while __slug in slugs:
            counter += 1
            __slug = "%s_%d" % (slug, counter)
        j.slug = __slug
        j.name = job_name
        j.site = g.site.domain
        j.categories = [ c.strip() for c in request.form.get("categories").split(",") ]
        j.intro = request.form.get("intro")
        j.description = request.form.get("description")
        j.slides = []
        texts = request.form.getlist("text")
        image_urls = request.form.getlist("image_url")
        captions = request.form.getlist("caption")
        caption_links = request.form.getlist("caption_link")
        for text, image_url, caption, caption_link in zip(texts, image_urls, captions, caption_links):
            if text or image_url:
                j.slides.append(Slide(text=text, image_url=image_url, caption=caption, caption_link=caption_link))
        j.save()
        portfolio.jobs.append(j)
        portfolio.save()
        return redirect(url_for(".job", slug=j.slug))
    return render_template("edit_job.html", job=j)

@portfolio.route("/<slug>/e", methods=["POST", "GET"])
def edit_job(slug):
    try:
        j = Job.objects.get(site=g.site.domain, slug=slug)
    except Job.DoesNotExist:
        abort(404)

    if not g.site.domain == g.user:
        abort(403)

    if request.method == "POST":
        j.name = request.form.get("name")
        #j.slug = slugify(j.name)
        j.categories = [ c.strip() for c in request.form.get("categories").split(",") ]
        j.intro = request.form.get("intro")
        j.description = request.form.get("description")
        j.slides = []
        texts = request.form.getlist("text")
        image_urls = request.form.getlist("image_url")
        captions = request.form.getlist("caption")
        caption_links = request.form.getlist("caption_link")
        for text, image_url, caption, caption_link in zip(texts, image_urls, captions, caption_links):
            if text or image_url:
                j.slides.append(Slide(text=text, image_url=image_url, caption=caption, caption_link=caption_link))
        j.save()
        return redirect(url_for(".job", slug=j.slug))

    return render_template("edit_job.html", job=j)
