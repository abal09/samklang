#!/usr/bin/env python
# coding: utf-8

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, session, g, flash
from werkzeug import secure_filename
from flask.ext.mongoengine import MongoEngine
from flask_mail import Mail, Message
from flask.ext.babel import Babel, format_datetime, format_date, format_time
from flask.ext.babel import gettext as _
from models import Site, File, Menu, MenuLink, LoginToken
from utils import save_file
from blog import blog
from pages import pages
from portfolio import portfolio
from personnel import personnel

from hashlib import sha1

app = Flask(__name__, instance_relative_config=True)
app.register_blueprint(blog)
app.register_blueprint(portfolio)
app.register_blueprint(personnel)
app.register_blueprint(pages)
app.config.from_object('config')
app.config.from_pyfile('config.cfg', silent=True)
db = MongoEngine(app)
mail = Mail(app)
babel = Babel(app)

app.jinja_env.filters['datetime'] = format_datetime
app.jinja_env.filters['date'] = format_date
app.jinja_env.filters['time'] = format_time

import logging
file_handler = logging.FileHandler(app.config.get("LOGFILE", 'samklang.log'))
file_handler.setLevel(logging.WARNING)
app.logger.addHandler(file_handler)

admins = app.config.get("ADMINS", [])
error_sender = app.config.get("MAIL_ERROR_SENDER", "no-reply@localhost")
smtp_server = app.config.get("MAIL_SERVER", "localhost")
if admins and error_sender and smtp_server and not app.debug:
    recipients = []
    for admin in admins:
        if isinstance(admin, tuple):
            recipients.append("%s <%s>" % admin)
        else:
            recipients.append(admin)

    import logging
    from logging.handlers import SMTPHandler
    mail_handler = SMTPHandler(smtp_server, error_sender, recipients,
            _('Samklang Error'))
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

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
        if not app.config.get("DOMAIN_ROOT"):
            return _("Config is missing a DOMAIN_ROOT: the domain name of your "
                    "main site.")
        if not app.config.get("ADMINS"):
            return _("Config is missing ADMINS: used for login to your "
                    "first site and recipient of error messages.")
        name = app.config.get("ROOT_SITE_NAME", _("Your new site"))
        description = _("This is your new site. This is also your root site, "
                "and this can be used to create other sites.")

        root_site, created = Site.objects.get_or_create(
                domain=app.config.get("DOMAIN_ROOT"),
                defaults={
                    "name": name,
                    "description" :"<h1>%s</h1><p>%s</p>" % (
                        name, description),
                    "owner_email": None,
                    "verified_email": True
                    })
        port = app.config.get("PORT", None)
        url = "//%s" % root_site.domain
        if port:
            url += ":%d" % port
        if created:
            return redirect(url)
        else:
            return redirect("%s%s" % (url, url_for("sites")))

    g.user = session.get("username", None)
    if "menu" in g.site.active_modules:
        g.menu, created = Menu.objects.get_or_create(site=g.site.domain)
    else:
        g.menu = None

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
        admin_found = False
        if not g.site.owner_email and g.site.domain == app.config.get("DOMAIN_ROOT"):
            for admin in app.config.get("ADMINS"):
                if email == admin[1]:
                    admin_found = True
                    break

        if email != g.site.owner_email and not admin_found:
            flash(
                    _("That email address (%(email)s) does not match the owner "
                        "email address of this domain",
                        email=email))
            return redirect(url_for("login"))

        root_domain = app.config.get("DOMAIN_ROOT")
        port = app.config.get("PORT", None)

        code = sha1()
        code.update(g.site.domain)
        code.update(email)
        code.update(app.config["SECRET_KEY"])

        token = LoginToken()
        token.site = g.site.domain
        token.code = code.hexdigest()
        token.save()

        host = g.site.domain
        if root_domain:
            host += ".%s" % root_domain
        if port:
            host += ":%d" % port

        message = Message(_("Log in to %(host)s", host=g.site.domain),
                recipients=[email],
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
            "You should soon get an email soon. Click the link inside it to log in."
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
    try:
        LoginToken.objects.get(code=verification_code, site=g.site.domain)
        # TODO: add time limit check on previous line
    except:
        return _("The verification code is wrong or too old")
    else:
        session["username"] = g.site.domain
        flash(_("You are now logged in"))
        return redirect(url_for('index'))

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
            conflicting_site = Site.objects.filter(domain=site.domain).first()
            if not conflicting_site:
                site.description = _("<h1>Introductory text</h1><p>This should "
                        "contain simple help about what is changeable and how."
                        "</p>")
                site.save()
                url = "//%s" % site.domain
                if root_domain:
                    url += ".%s" % root_domain
                if port:
                    url += ":%d" % port
                return redirect(url)
        return redirect(url_for("sites"))
    if root_domain == g.site.domain:
        sites = Site.objects.all()
    else:
        sites = Site.objects.filter(domain__endswith=g.site.domain)
    return render_template("sites.html", sites=sites, root_domain=root_domain, port=port)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/edit", methods=["POST", "GET"])
def edit():
    site = g.site
    if request.method == "POST" and g.site.domain == g.user:
        if request.files["header_image"]:
            site.header_image, length = save_file(request.files["header_image"], app.config["UPLOAD_FOLDER"])
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

@app.route("/files/", methods=["POST", "GET"])
def files():
    if request.method == "POST" and g.site.domain == g.user:
        reqfile = request.files['file']
        f = File()
        f.site = g.site.domain
        f.name = reqfile.filename
        f.slug = secure_filename(f.name)
        f.content_type = reqfile.mimetype
        f.slug, f.content_length = save_file(reqfile, app.config["UPLOAD_FOLDER"])
        f.save()

    files = File.objects(site=g.site.domain)
    return render_template('files.html', files=files)

@app.route("/a/l/", methods=["POST", "GET"])
def menu():
    if "menu" in g.site.active_modules:
        menu = g.menu

    if request.method == "POST" and g.site.domain == g.user:
        if "username" in session and g.user == g.site.domain:
                texts = request.form.getlist("text")
                links = request.form.getlist("link")
                menu.links = []
                for text, link in zip(texts, links):
                    if text and link:
                        menu.links.append(MenuLink(text=text, link=link))
                simple = request.form.get("simple", False)
                print simple
                if simple:
                    menu.simple = True
                else:
                    menu.simple = False
                menu.text_color = request.form.get("text_color", None)
                menu.active_text_color = request.form.get("active_text_color", None)
                menu.hover_text_color = request.form.get("hover_text_color", None)
                menu.background_color = request.form.get("background_color", None)
                menu.active_background_color = request.form.get("active_background_color", None)
                menu.hover_background_color = request.form.get("hover_background_color", None)
                menu.save()
        return redirect(url_for("index"))

    return render_template("menu.html")

@app.route("/a/m/", methods=["POST", "GET"])
def modules():
    available_modules = ["menu", "pages", "blog", "portfolio", "personnel"]

    if request.method == "POST" and g.user == g.site.domain:
        site_changed = False
        for module in available_modules:
            module_active = request.form.get("%s_active" % module)
            if module_active:
                if not module in g.site.active_modules:
                    g.site.active_modules.append(module)
                    site_changed = True
            else:
                if module in g.site.active_modules:
                    g.site.active_modules.remove(module)
                    site_changed = True
        if site_changed:
            g.site.save()

        return redirect(url_for("modules"))

    return render_template("modules.html", modules=available_modules)

if __name__ == "__main__":
    app.run()
