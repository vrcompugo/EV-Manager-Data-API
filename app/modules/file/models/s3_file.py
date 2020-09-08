from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields
import uuid
import base64
from ..minio import get_file_public, make_public

from app import db

from ..minio import get_file


class S3File(db.Model):
    __versioned__ = {}
    __tablename__ = "s3_file"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(UUID(as_uuid=True), unique=True, nullable=False)
    model = db.Column(db.String(80))
    model_id = db.Column(db.Integer)
    uploaded = db.Column(db.DateTime)
    filename = db.Column(db.String(120))

    @hybrid_property
    def public_link(self):
        return get_file_public(str(self.uuid), self.filename, 30)

    @hybrid_property
    def longterm_public_link(self, days=90):
        from ..file_services import encode_file_token
        token = base64.b64encode(encode_file_token(self.id, days=days)).decode('utf-8')
        return f"https://api.korbacher-energiezentrum.de/files/view/{token}"

    def make_public(self):
        return make_public(str(self.uuid), self.filename)

    def get_file(self):
        return get_file(str(self.uuid), self.filename)


class S3FileSchema(ModelSchema):

    versions = fields.Constant([])
    public_link = fields.String()

    class Meta:
        model = S3File
