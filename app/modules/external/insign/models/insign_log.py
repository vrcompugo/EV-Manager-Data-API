from datetime import datetime
from app import db


class InsignLog(db.Model):
    __tablename__ = "insign_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    datetime = db.Column(db.DateTime)
    lead_id = db.Column(db.Integer)
    session_id = db.Column(db.String(120))
    data = db.Column(db.JSON)
