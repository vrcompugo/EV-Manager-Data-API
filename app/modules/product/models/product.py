from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields

from app import db
from app.modules.customer.models.customer import CustomerSchema
from app.modules.user.models.user_role import UserRoleShortSchema


class Product(db.Model):
    __versioned__ = {}
    __tablename__ = "product"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    number = db.Column(db.String(20))
    tollnumber = db.Column(db.String(80))
    product_group = db.Column(db.String(80))
    name = db.Column(db.String(120))
    weight = db.Column(db.Numeric(scale=4, precision=12))
    width = db.Column(db.Numeric(scale=4, precision=12))
    length = db.Column(db.Numeric(scale=4, precision=12))
    height = db.Column(db.Numeric(scale=4, precision=12))
    ean = db.Column(db.String(120))
    purchase_unit = db.Column(db.Numeric(scale=4, precision=12))
    reference_unit = db.Column(db.Numeric(scale=4, precision=12))
    pack_unit = db.Column(db.String(40))
    shipping_time = db.Column(db.String(60))
    tax_rate = db.Column(db.Integer)
    min_purchase = db.Column(db.Integer)
    price_net = db.Column(db.Numeric(scale=4, precision=12))
    discount_percent = db.Column(db.Numeric(scale=4, precision=12))
    cost = db.Column(db.Numeric(scale=4, precision=12))
    active = db.Column(db.Boolean)

    @hybrid_property
    def search_query(self):
        return db.session.query(Product)


class ProductSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = Product
