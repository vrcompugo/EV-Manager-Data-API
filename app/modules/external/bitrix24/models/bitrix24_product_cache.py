from app import db
from sqlalchemy.dialects.postgresql import JSONB


class Bitrix24ProductCache(db.Model):
    __tablename__ = "bitrix24_product_cache"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.String(30))
    name = db.Column(db.String(255))
    catalog_id = db.Column(db.String(30))
    section_id = db.Column(db.String(30))
    datetime = db.Column(db.DateTime)
    data = db.Column(JSONB)
