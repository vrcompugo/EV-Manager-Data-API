from app import db
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields


class ImportIdAssociation(db.Model):
    __versioned__ = {}
    __tablename__ = "import_id_association"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source = db.Column(db.String(40))
    model = db.Column(db.String(60))
    local_id = db.Column(db.Integer)
    remote_id = db.Column(db.Integer)


class ImportIdAssociationSchema(ModelSchema):
    versions = fields.Constant([])

    class Meta:
        model = ImportIdAssociation
