from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields
from enum import Enum

from app import db
from app.modules.customer.models.customer import CustomerSchema
from app.modules.reseller.models.reseller import ResellerSchema


class OfferV2Item(db.Model):
    __versioned__ = {}
    __tablename__ = "offer_v2_items"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    offer_id = db.Column(db.Integer, db.ForeignKey("offer_v2.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    product = db.relationship("Product")
    sort = db.Column(db.Integer)
    number = db.Column(db.String(50))
    label = db.Column(db.String(200))
    description = db.Column(db.Text)
    data = db.Column(db.JSON)
    calculation = db.Column(db.JSON)
    price_definition = db.Column(db.JSON)
    weight_single = db.Column(db.Numeric(scale=4, precision=12))
    weight_total = db.Column(db.Numeric(scale=4, precision=12))
    quantity = db.Column(db.Numeric(scale=4, precision=12))
    quantity_unit = db.Column(db.String(50))
    cost = db.Column(db.Numeric(scale=4, precision=12))
    tax_rate = db.Column(db.Integer)
    single_price = db.Column(db.Numeric(scale=4, precision=12))
    single_price_net = db.Column(db.Numeric(scale=4, precision=12))
    single_tax_amount = db.Column(db.Numeric(scale=4, precision=12))
    discount_rate = db.Column(db.Numeric(scale=4, precision=12))
    discount_single_amount = db.Column(db.Numeric(scale=4, precision=12))
    discount_single_price = db.Column(db.Numeric(scale=4, precision=12))
    discount_single_price_net = db.Column(db.Numeric(scale=4, precision=12))
    discount_single_price_net_overwrite = db.Column(db.Numeric(scale=4, precision=12))
    discount_single_tax_amount = db.Column(db.Numeric(scale=4, precision=12))
    discount_total_amount = db.Column(db.Numeric(scale=4, precision=12))
    total_price = db.Column(db.Numeric(scale=4, precision=12))
    total_price_net = db.Column(db.Numeric(scale=4, precision=12))
    total_tax_amount = db.Column(db.Numeric(scale=4, precision=12))
    last_updated = db.Column(db.DateTime)

    @hybrid_property
    def search_query(self):
        return db.session.query(OfferV2Item)


class OfferV2ItemsSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = OfferV2Item
