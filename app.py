from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, safe_join, session, g, flash
from werkzeug import secure_filename
from flask.ext.mongoengine import MongoEngine
from flask.ext.sendmail import Mail, Message
from models import Site, File

from hashlib import sha1
import os

app = Flask(__name__)
app.config.from_pyfile('config.py')
db = MongoEngine(app)
mail = Mail(app)

@app.before_request
def add_site():
    g.site = Site.get_by_hostname(request.host)
    g.user = session.get("username", None)

# fake login
@app.route("/login", methods=["POST", "GET"])
def login():
    if not g.site.verified_email:
        #flash("You should set up a verified email address first.")
        #return redirect(url_for("add_email"))

        # log in without security
        flash('Everybody can log in to your site and do changes until you add '
                'an <a href="%s">owner email address</a>.' %
                url_for("add_email"), 'secondary')
        session["username"] = g.site.domain
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", None)
        if email != g.site.owner_email:
            flash("That email address (%s) does not match the owner email "
                    "address of this domain" % email)
            return redirect(url_for("login"))

        root_domain = app.config.get("DOMAIN_ROOT", None)
        port = app.config.get("PORT", 5000)

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

        message = Message("Log in to samklang",
                sender=("Samklang", "post@samklang.no"),
                recipients=[g.site.owner_email],
                )
        message.body = (
                "Log in to samklang by clicking the following link:\r\n\r\n" +
                "http://%s%s\r\n\r\n" % (host, url_for('email_login', verification_code=code.hexdigest())) +
                "Kthxbye\r\n")
        mail.send(message)
        flash("You should get an email soon. Click the link inside it to log in.")
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route("/admin/email/add", methods=["POST", "GET"])
def add_email():
    if request.method == "POST":
        root_domain = app.config.get("DOMAIN_ROOT", None)
        port = app.config.get("PORT", 5000)
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

            message = Message("Verify your email",
                    sender=("Samklang", "post@samklang.no"),
                    recipients=[email],
                    )
            message.body = (
                    "Thanks for trying Samklang\r\n\r\n" +
                    "Click the following link to verify that this address worked:\r\n" +
                    "http://%s%s\r\n\r\n" % (host, url_for('email_verify', verification_code=code.hexdigest())) +
                    "Kthxbye\r\n")
            mail.send(message)
            flash("You should get an email soon. Click the link inside it to verify the address worked.")
            return redirect(url_for("index"))
    else:
        if g.site.verified_email and "username" not in session:
            return "Email already set, you need to log in using the old email address before you can set a new email address."
    return render_template("add_email.html")

@app.route("/login/<verification_code>")
def email_login(verification_code):
    code = sha1()
    code.update(g.site.domain)
    code.update(g.site.owner_email)
    code.update(app.config["SECRET_KEY"])

    if verification_code == code.hexdigest():
        session["username"] = g.site.domain
        flash("You are now logged in")
        return redirect(url_for('index'))
    else:
        return "The verification code is wrong"

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
        flash("Your site is now verified and you are logged in")
        return redirect(url_for('index'))
    else:
        return "The verification code is wrong"

@app.route("/sites", methods=["POST", "GET"])
def sites():
    root_domain = app.config.get("DOMAIN_ROOT", None)
    port = app.config.get("PORT", 5000)
    if request.method == "POST":
        domain = request.form["domain"]
        name = request.form["name"]
        if domain and name:
            site = Site()
            site.name = name.strip()
            site.domain = domain.strip()
            site.description = "<h1>Introductory text</h1><p>This should contain simple help about what is changeable and how.</p>"
            conflicting_site = Site.objects.filter(domain=site.domain).first()
            if not conflicting_site:
                site.save()
                flash("You now have a new site. Play around with it for up to 24 hours, or register to keep it.")
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
    if request.method == "POST":
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
    f = File.objects.get(id=id)
    f.delete()
    return jsonify(status=True)

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
    if request.method == "POST":
        reqfile = request.files['file']
        f = File()
        f.name = reqfile.filename
        f.slug = secure_filename(f.name)
        f.content_type = reqfile.mimetype
        f.slug, f.content_length = save_file(reqfile)
        f.save()

    files = File.objects.all()
    return render_template('files.html', files=files)

if __name__ == "__main__":
    app.run()
