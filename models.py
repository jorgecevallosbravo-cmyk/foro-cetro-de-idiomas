from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Table(db.Model):
    __tablename__ = "tables"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    passcode = db.Column(db.String(4), nullable=False)
    locked = db.Column(db.Boolean, default=False, nullable=False)
    apoyos = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    resolution = db.relationship(
        "Resolution",
        backref="table",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Resolution(db.Model):
    __tablename__ = "resolutions"

    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey("tables.id"), nullable=False, unique=True)
    problemas = db.Column(db.Text, default="")
    propuestas = db.Column(db.Text, default="")
    accion_prioritaria = db.Column(db.Text, default="")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
