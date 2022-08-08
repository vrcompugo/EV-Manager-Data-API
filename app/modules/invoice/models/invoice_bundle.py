from app import db
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import JSONB
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields
from app.basemodel import BaseModel


class InvoiceBundle(BaseModel, db.Model):
    __tablename__ = "invoice_bundle"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kw = db.Column(db.Integer)
    year = db.Column(db.Integer)
    items_count = db.Column(db.Integer)
    is_complete = db.Column(db.Boolean)
    is_running = db.Column(db.Boolean)
    download_link = db.Column(db.String(250))
    download_datetime = db.Column(db.DateTime)
    download_by_user_id = db.Column(db.Integer)
    import_datetime = db.Column(db.DateTime)
    import_by_user_id = db.Column(db.Integer)
    comment = db.Column(db.String(250))

    @hybrid_property
    def download_links(self):
        from app.models import S3File
        links = []
        files = S3File.query.filter(S3File.model.like("invoice_bundle-%")).filter(S3File.model_id == self.id).all()
        for file in files:
            links.append(file.public_link)
        return links
