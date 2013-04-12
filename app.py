from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, safe_join, session, g
from werkzeug import secure_filename
from flask.ext.mongoengine import MongoEngine
from models import Site, File

from hashlib import sha1
import os

app = Flask(__name__)
app.config.from_pyfile('config.py')
db = MongoEngine(app)

@app.before_request
def add_site():
    g.site = Site.get_by_hostname(request.host)

# fake login
@app.route("/login", methods=["POST", "GET"])
def login():
    session['username'] = "user"
    return redirect(url_for('index'))

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route("/sites", methods=["POST", "GET"])
def sites():
    if request.method == "POST":
        domain = request.form["domain"]
        name = request.form["name"]
        if domain and name:
            site = Site()
            site.name = name.strip()
            site.domain = domain.strip()
            conflicting_site = Site.objects.filter(domain=site.domain).first()
            if not conflicting_site:
                site.save()
        return redirect(url_for("sites"))
    sites = Site.objects.all()  # use this for checking if domain name is available
    return render_template("sites.html", sites=sites)

@app.route("/", methods=["POST", "GET"])
def index():
    site, created = Site.objects.get_or_create(domain="eksempel.no", name="Eksempelnettsted")
    if request.method == "POST":
        if request.files["header_image"]:
            site.header_image, length = save_file(request.files["header_image"])
        site.footers = []
        footers = request.form.getlist("footer")
        print footers
        for footer in footers:
            if footer:
                site.footers.append(footer)
        site.description = request.form["description"]
        site.save()
        return redirect(url_for("index"))
    if request.args.get('edit'):
        edit = True
    else:
        edit = False
    return render_template('index.html', description=site.description, edit=edit)

@app.route("/media/<path:filename>")
def media(filename):
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
    app.run(debug=True)
