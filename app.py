from flask import Flask, render_template, request, redirect, url_for
from flask.ext.mongoengine import MongoEngine
from models import Site

app = Flask(__name__)
app.config.from_pyfile('config.py')
db = MongoEngine(app)

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

if __name__ == "__main__":
    app.run(debug=True)
