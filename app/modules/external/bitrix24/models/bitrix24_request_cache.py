from app import db
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import JSONB


class Bitrix24RequestCache(db.Model):
    __tablename__ = "bitrix24_request_cache"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    method = db.Column(db.String(20))
    url = db.Column(db.String(255))
    parameters = db.Column(JSONB)
    post_data = db.Column(JSONB)
    domain = db.Column(db.String(255))
    datetime = db.Column(db.DateTime)
    cached_responses = db.Column(db.Integer)
    fresh_response = db.Column(db.Integer)
    response = db.Column(JSONB)
