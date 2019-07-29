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
    type = db.Column(db.String(80))
    name = db.Column(db.String(80))

    @hybrid_property
    def search_query(self):
        return db.session.query(Product)


class ProductSchema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = Product
