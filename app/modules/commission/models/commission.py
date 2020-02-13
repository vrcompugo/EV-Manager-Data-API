from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.postgresql import TEXT
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db


class Commission(db.Model):
    __versioned__ = {}
    __tablename__ = "commission"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    number = db.Column(db.String(20))
    year = db.Column(db.Integer)
    month = db.Column(db.Integer)
    reseller_id = db.Column(db.Integer, db.ForeignKey("reseller.id"))
    reseller = db.relationship("Reseller")
    taxrate = db.Column(db.Integer)
    extra_item = db.Column(db.Text)
    extra_value_net = db.Column(db.Numeric(scale=4, precision=12))
    comment_internal = db.Column(db.Text)
    comment_external = db.Column(db.Text)
    is_checked = db.Column(db.Boolean)
    is_paid = db.Column(db.Boolean)

    @hybrid_property
    def search_query(self):
        return db.session.query(Commission)


class CommissionSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = Commission
