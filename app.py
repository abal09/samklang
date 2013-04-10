from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, safe_join, session
from werkzeug import secure_filename
from flask.ext.mongoengine import MongoEngine
from models import Site, File

from hashlib import sha1
import os

app = Flask(__name__)
app.config.from_pyfile('config.py')
db = MongoEngine(app)

# fake login
@app.route("/login", methods=["POST", "GET"])
def login():
    session['username'] = "user"
    return redirect(url_for('index'))

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route("/", methods=["POST", "GET"])
def index():
    site, created = Site.objects.get_or_create(domain="eksempel.no", name="Eksempelnettsted")
    if request.method == "POST":
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
    hsh = sha1()
    hsh.update("blob %u\0" % len(data))
    hsh.update(data)
    return hsh.hexdigest()

@app.route("/files/", methods=["POST", "GET"])
def files():
    if request.method == "POST":
        reqfile = request.files['file']
        f = File()
        f.name = reqfile.filename
        f.slug = secure_filename(f.name)
        f.content_type = reqfile.mimetype
        reqfile_path = safe_join(app.config['UPLOAD_FOLDER'], f.slug)
        reqfile.save(reqfile_path)
        f.content_length = os.path.getsize(reqfile_path)
        with file(reqfile_path) as __f:
            f.ghash = githash(__f.read())
        new_dir = safe_join(app.config['UPLOAD_FOLDER'], f.ghash[0:2])
        new_filename = f.ghash[2:40]
        new_path = safe_join(new_dir, new_filename)
        print f.content_length
        try:
            os.makedirs(new_dir)
        except OSError:
            pass  # dir already exists: OK
        os.rename(reqfile_path, new_path)
        f.slug = safe_join(f.ghash[0:2], f.ghash[2:40])
        f.save()

    files = File.objects.all()
    return render_template('files.html', files=files)

if __name__ == "__main__":
    app.run(debug=True)
