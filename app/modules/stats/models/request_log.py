from tokenize import group
from app import db
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import JSONB


class RequestLog(db.Model):
    __tablename__ = "request_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    url = db.Column(db.String(255))
    route = db.Column(db.String(255))
    method = db.Column(db.String(20))
    post_data = db.Column(JSONB)
    json = db.Column(JSONB)
    datetime = db.Column(db.DateTime)
    duration_milliseconds = db.Column(db.Integer)
