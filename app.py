#!/usr/bin/env python
# coding: utf-8

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, safe_join, session, g, flash, abort
from werkzeug import secure_filename
from flask.ext.mongoengine import MongoEngine
from flask.ext.sendmail import Mail, Message
from flask.ext.babel import Babel
from flask.ext.babel import gettext as _
from models import Site, File, Page, MenuLink, Portfolio, Job, Slide

from hashlib import sha1
import os

app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.cfg', silent=True)
db = MongoEngine(app)
mail = Mail(app)
babel = Babel(app)

@babel.localeselector
def get_locale():
    # if a user is logged in, use the locale from the user settings
    #user = getattr(g, 'user', None)
    #if user is not None:
        #return user.locale
    # otherwise try to guess the language from the user accept
    return request.accept_languages.best_match(['en', 'nb'])

@babel.timezoneselector
def get_timezone():
    #user = getattr(g, 'user', None)
    #if user is not None:
        #return user.timezone
    pass

@app.before_request
def add_site():
    g.site = Site.get_by_hostname(request.host, app.config.get("DOMAIN_ROOT"))
    if g.site is None:
        abort(404)
    g.user = session.get("username", None)

# fake login
@app.route("/login", methods=["POST", "GET"])
def login():
    if not g.site.verified_email:
        #flash("You should set up a verified email address first.")
        #return redirect(url_for("add_email"))

        # log in without security
        flash(
                _('Everybody can log in to your site and do changes until you '
                    'add an <a href="%(url)s">owner email address</a>.',
                    url=url_for("add_email")),
                'secondary')
        session["username"] = g.site.domain
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", None)
        if email != g.site.owner_email:
            flash(
                    _("That email address (%(email)s) does not match the owner "
                        "email address of this domain",
                        email=email))
            return redirect(url_for("login"))

        root_domain = app.config.get("DOMAIN_ROOT")
        port = app.config.get("PORT", None)

        code = sha1()
        code.update(g.site.domain)
        code.update(g.site.owner_email)
        code.update(app.config["SECRET_KEY"])
        # TODO; Add some timing requirements as well

        host = g.site.domain
        if root_domain:
            host += ".%s" % root_domain
        if port:
            host += ":%d" % port

        message = Message(_("Log in to %(host)s", host=g.site.domain),
                sender=("Samklang", "login@samklang.no"),
                recipients=[g.site.owner_email],
                )
        message.body = _(
                "Log in to samklang by clicking the following link:\r\n\r\n"
                "http://%(host)s%(url)s\r\n\r\nKthxbye\r\n",
                host=host,
                url=url_for(
                    'email_login',
                    verification_code=code.hexdigest()
                    ),
                )
        mail.send(message)
        flash(_(
            "You should soon get an soon. Click the link inside it to log in."
            ))
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route("/admin/email/add", methods=["POST", "GET"])
def add_email():
    if request.method == "POST":
        root_domain = app.config.get("DOMAIN_ROOT")
        port = app.config.get("PORT", None)
        email = request.form.get("email", None)
        if email:
            g.site.owner_email = email
            g.site.save()

            code = sha1()
            code.update(g.site.domain)
            code.update(g.site.owner_email)
            code.update(app.config["SECRET_KEY"])
            # TODO; Add some timing requirements as well

            host = g.site.domain
            if root_domain:
                host += ".%s" % root_domain
            if port:
                host += ":%d" % port

            message = Message(_("Verify your email"),
                    sender=("Samklang", "login@samklang.no"),
                    recipients=[email],
                    )
            message.body = _(
                    "Thanks for trying Samklang\r\n\r\n"
                    "Click the following link to verify that this address worked:\r\n"
                    "http://%(host)s%(url)s\r\n\r\nKthxbye\r\n",
                    host=host,
                    url=url_for('email_verify', verification_code=code.hexdigest()))
            mail.send(message)
            flash(_("You should soon get an email soon. Click the link inside"
                " it to verify the address worked."))
            return redirect(url_for("index"))
    else:
        if g.site.verified_email and "username" not in session:
            return _("Email already set, you need to log in using the old email"
                    " address before you can set a new email address.")
    return render_template("add_email.html")

@app.route("/login/<verification_code>")
def email_login(verification_code):
    code = sha1()
    code.update(g.site.domain)
    code.update(g.site.owner_email)
    code.update(app.config["SECRET_KEY"])

    if verification_code == code.hexdigest():
        session["username"] = g.site.domain
        flash(_("You are now logged in"))
        return redirect(url_for('index'))
    else:
        return _("The verification code is wrong")

@app.route("/admin/keep/<verification_code>")
def email_verify(verification_code):
    code = sha1()
    code.update(g.site.domain)
    code.update(g.site.owner_email)
    code.update(app.config["SECRET_KEY"])

    if verification_code == code.hexdigest():
        g.site.verified_email = True
        g.site.save()

        session["username"] = g.site.domain
        flash(_("Your site is now verified and you are logged in"))
        return redirect(url_for('index'))
    else:
        return _("The verification code is wrong")

@app.route("/sites", methods=["POST", "GET"])
def sites():
    root_domain = app.config.get("DOMAIN_ROOT")
    port = app.config.get("PORT", None)
    if request.method == "POST":
        domain = request.form["domain"]
        name = request.form["name"]
        if domain and name:
            site = Site()
            site.name = name.strip()
            site.domain = domain.strip()
            site.description = _("<h1>Introductory text</h1><p>This should "
                    "contain simple help about what is changeable and how."
                    "</p>")
            conflicting_site = Site.objects.filter(domain=site.domain).first()
            if not conflicting_site:
                site.save()
                flash(_("You now have a new site. Play around with it for some "
                    "time, or register by verifying your email address to keep "
                    "it."))
                url = "//%s" % site.domain
                if root_domain:
                    url += ".%s" % root_domain
                if port:
                    url += ":%d" % port
                return redirect(url)
        return redirect(url_for("sites"))
    sites = Site.objects.all()  # use this for checking if domain name is available
    return render_template("sites.html", sites=sites, root_domain=root_domain, port=port)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/edit", methods=["POST", "GET"])
def edit():
    site = g.site
    if request.method == "POST" and g.site.domain == g.user:
        if request.files["header_image"]:
            site.header_image, length = save_file(request.files["header_image"])
        site.footers = []
        footers = request.form.getlist("footer")
        for footer in footers:
            if footer:
                site.footers.append(footer)
        site.name = request.form["name"]
        site.description = request.form["description"]
        site.save()
        return redirect(url_for("index"))
    return render_template('edit.html')

@app.route("/media/<path:filename>")
@app.route("/media/<path:filename>.<suffix>")
def media(filename, suffix=None):
    if suffix:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    else:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/files/delete/<id>", methods=["POST"])
def files_delete(id):
    if g.site.domain == g.user:
        f = File.objects.get(id=id)
        f.delete()
        return jsonify(status=True)
    else:
        return jsonify(status=False)

def githash(data):
    length = len(data)
    hsh = sha1()
    hsh.update("blob %u\0" % length)
    hsh.update(data)
    return hsh.hexdigest(), length

def save_file(reqfile):
    reqfile_path = safe_join(app.config['UPLOAD_FOLDER'], secure_filename(reqfile.filename))
    reqfile.save(reqfile_path)
    with file(reqfile_path) as __f:
        ghash, length = githash(__f.read())
    new_dir = safe_join(app.config['UPLOAD_FOLDER'], ghash[0:2])
    new_filename = ghash[2:40]
    new_path = safe_join(new_dir, new_filename)
    try:
        os.makedirs(new_dir)
    except OSError:
        pass  # dir already exists: OK
    os.rename(reqfile_path, new_path)
    return safe_join(ghash[0:2], ghash[2:40]), length

@app.route("/files/", methods=["POST", "GET"])
def files():
    if request.method == "POST" and g.site.domain == g.user:
        reqfile = request.files['file']
        f = File()
        f.site = g.site.domain
        f.name = reqfile.filename
        f.slug = secure_filename(f.name)
        f.content_type = reqfile.mimetype
        f.slug, f.content_length = save_file(reqfile)
        f.save()

    files = File.objects(site=g.site.domain)
    return render_template('files.html', files=files)

@app.route("/menu/", methods=["POST", "GET"])
def menu():
    if request.method == "POST" and g.site.domain == g.user:
        if "username" in session and g.user == g.site.domain:
            texts = request.form.getlist("text")
            links = request.form.getlist("link")
            g.site.menu_links = []
            for text, link in zip(texts, links):
                if text and link:
                    g.site.menu_links.append(MenuLink(text=text, link=link))
            g.site.save()
        return redirect(url_for("menu"))

    return render_template("menu.html", menu_links=g.site.menu_links)

# portfolio
@app.route("/p/")
def portfolio():
    try:
        p = Portfolio.objects.get(site=g.site.domain)
        if not p.active:
            raise(Portfolio.DoesNotExist)
    except Portfolio.DoesNotExist:
        abort(404)
    return render_template("portfolio.html", portfolio=p)

@app.route("/p/e", methods=["POST", "GET"])
def edit_portfolio():
    if not g.site.domain == g.user:
        abort(403)
    try:
        p = Portfolio.objects.get(site=g.site.domain)
    except Portfolio.DoesNotExist:
        p = Portfolio.objects.create(site=g.site.domain)

    if request.method == "POST":
        p.active = True
        p.site = g.site.domain
        p.title = request.form.get("title")
        p.intro = request.form.get("intro")
        p.save()
        return redirect(url_for("portfolio"))

    return render_template("edit_portfolio.html", portfolio=p)

@app.route("/p/<slug>")
def job(slug):
    try:
        j = Job.objects.get(site=g.site.domain, slug=slug)
    except Job.DoesNotExist:
        abort(404)
    return render_template("job.html", job=j)

@app.route("/p/n", methods=["POST", "GET"])
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
        return redirect(url_for("job", slug=j.slug))
    return render_template("edit_job.html", job=j)

@app.route("/p/<slug>/e", methods=["POST", "GET"])
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
        return redirect(url_for("job", slug=j.slug))

    return render_template("edit_job.html", job=j)

def slugify(value):
    """
    Normalizes a string using unidecode library. Lowercase it, remove
    punctuation and replace spacing with hyphens.

    >>> slugify(u'Blåbærsyltetøy')
    'Blabaersyltetoy'
    """
    from unidecode import unidecode
    import re

    value = unidecode(value)
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return unicode(re.sub('[-\s]+', '-', value))

@app.route("/pages/", methods=["POST", "GET"])
def pages():
    if request.method == "POST" and g.site.domain == g.user:
        name = request.form['name']
        if name:
            p = Page()
            p.name = name
            p.slug = slugify(name)
            p.site = g.site.domain
            p.save()
            return redirect(url_for("edit_page", slug=p.slug))
    pages = Page.objects(site=g.site.domain)
    return render_template('pages.html', pages=pages)

@app.route("/<slug>/")
def page(slug):
    try:
        page = Page.objects.get(slug=slug, site=g.site.domain)
    except Page.DoesNotExist:
        abort(404)
    return render_template("page.html", page=page)

@app.route("/<slug>/edit", methods=["POST", "GET"])
def edit_page(slug):
    try:
        page = Page.objects.get(slug=slug, site=g.site.domain)
    except Page.DoesNotExist:
        abort(404)

    if request.method == "POST" and g.site.domain == g.user:
        page.name = request.form["name"]
        page.content = request.form["content"]
        page.save()
        return redirect(url_for("page", slug=page.slug))
    return render_template("edit_page.html", page=page)


if __name__ == "__main__":
    app.run()
