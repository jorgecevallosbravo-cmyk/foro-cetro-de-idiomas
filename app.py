import os
import random
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, Table, Resolution

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

database_url = os.environ.get("DATABASE_URL", "sqlite:///mesas.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 280,
}

db.init_app(app)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped


def generate_passcode():
    return "{:04d}".format(random.randint(0, 9999))


def lines_to_list(text):
    if not text:
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


app.jinja_env.filters["lines_to_list"] = lines_to_list


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/publico")
def publico_list():
    tables = Table.query.order_by(Table.name).all()
    return render_template("publico_list.html", tables=tables)


@app.route("/publico/<int:table_id>")
def publico_detail(table_id):
    table = Table.query.get_or_404(table_id)
    resolution = table.resolution
    return render_template("publico_detail.html", table=table, resolution=resolution)


@app.route("/publico/<int:table_id>/apoyar", methods=["POST"])
def publico_apoyar(table_id):
    table = Table.query.get_or_404(table_id)
    table.apoyos = (table.apoyos or 0) + 1
    db.session.commit()
    return redirect(url_for("publico_detail", table_id=table_id))


@app.route("/mesa", methods=["GET", "POST"])
def mesa_login():
    tables = Table.query.order_by(Table.name).all()
    if request.method == "POST":
        table_id = int(request.form["table_id"])
        passcode = request.form.get("passcode", "").strip()
        table = Table.query.get(table_id)
        if table and table.passcode == passcode:
            session["mesa_table_id"] = table.id
            return redirect(url_for("mesa_form"))
        flash("Código incorrecto. Intenta de nuevo.")
    return render_template("mesa_login.html", tables=tables)


@app.route("/mesa/editar", methods=["GET", "POST"])
def mesa_form():
    table_id = session.get("mesa_table_id")
    if not table_id:
        return redirect(url_for("mesa_login"))
    table = Table.query.get_or_404(table_id)

    if request.method == "POST":
        if table.locked:
            flash("Esta mesa ya fue cerrada por el/la organizador(a).")
            return redirect(url_for("mesa_form"))
        resolution = table.resolution or Resolution(table_id=table.id)
        resolution.problemas = request.form.get("problemas", "")
        resolution.propuestas = request.form.get("propuestas", "")
        resolution.accion_prioritaria = request.form.get("accion_prioritaria", "")
        db.session.add(resolution)
        db.session.commit()
        flash("Resolución guardada.")
        return redirect(url_for("mesa_form"))

    return render_template("mesa_form.html", table=table, resolution=table.resolution)


@app.route("/mesa/salir")
def mesa_salir():
    session.pop("mesa_table_id", None)
    return redirect(url_for("landing"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin_panel"))
        flash("Contraseña incorrecta.")
    return render_template("admin_login.html")


@app.route("/admin/salir")
def admin_salir():
    session.pop("is_admin", None)
    return redirect(url_for("landing"))


@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_panel():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        topic = request.form.get("topic", "").strip()
        if name and topic:
            table = Table(name=name, topic=topic, passcode=generate_passcode())
            db.session.add(table)
            db.session.commit()
            flash("Mesa '" + name + "' creada. Código: " + table.passcode)
    tables = Table.query.order_by(Table.id).all()
    return render_template("admin.html", tables=tables)


@app.route("/admin/<int:table_id>/lock", methods=["POST"])
@admin_required
def admin_lock(table_id):
    table = Table.query.get_or_404(table_id)
    table.locked = not table.locked
    db.session.commit()
    return redirect(url_for("admin_panel"))


@app.route("/admin/<int:table_id>/eliminar", methods=["POST"])
@admin_required
def admin_delete(table_id):
    table = Table.query.get_or_404(table_id)
    db.session.delete(table)
    db.session.commit()
    return redirect(url_for("admin_panel"))


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
