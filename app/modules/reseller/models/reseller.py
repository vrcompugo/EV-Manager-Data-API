from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db
from ..models.reseller_group import ResellerGroupSchema


class Reseller(db.Model):
    __versioned__ = {}
    __tablename__ = "reseller"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User")
    group_id = db.Column(db.Integer, db.ForeignKey("reseller_group.id"))
    group = db.relationship("ResellerGroup")
    email = db.Column(db.String(120))
    name = db.Column(db.String(120))
    number = db.Column(db.String(120))
    access_key = db.Column(db.String(60))
    phone = db.Column(db.String(120))
    sales_center = db.Column(db.String(140))
    sales_range = db.Column(db.Integer)
    sales_lat = db.Column(db.Float)
    sales_lng = db.Column(db.Float)
    lead_balance = db.Column(db.Integer)

    @hybrid_property
    def search_query(self):
        return db.session.query(Reseller)


class ResellerSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = Reseller
