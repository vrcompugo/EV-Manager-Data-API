from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields
import uuid
import traceback
import base64
from io import StringIO, BytesIO

from ..minio import get_file_public, make_public

from app import db
from app.modules.external.bitrix24.drive import get_file_content, get_public_link

from ..minio import get_file, delete_file


class S3File(db.Model):
    __versioned__ = {}
    __tablename__ = "s3_file"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(UUID(as_uuid=True), unique=True, nullable=False)
    model = db.Column(db.String(80))
    model_id = db.Column(db.Integer)
    uploaded = db.Column(db.DateTime)
    filename = db.Column(db.String(120))
    bitrix_file_id = db.Column(db.Integer)
    is_s3_deleted = db.Column(db.Boolean)

    @hybrid_property
    def public_link(self):
        if self.bitrix_file_id is not None and self.bitrix_file_id > 0:
            return get_public_link(self.bitrix_file_id, 300)
        return get_file_public(str(self.uuid), self.filename, 30)

    @hybrid_property
    def longterm_public_link(self, days=90):
        from ..file_services import encode_file_token

        if self.bitrix_file_id is not None and self.bitrix_file_id > 0:
            return get_public_link(self.bitrix_file_id, days * 24 * 60)
        token = base64.b64encode(encode_file_token(self.id, days=days)).decode('utf-8')
        return f"https://api.korbacher-energiezentrum.de/files/view/{token}"

    def make_public(self):
        if self.bitrix_file_id is not None and self.bitrix_file_id > 0:
            return get_public_link(self.bitrix_file_id, 3 * 31 * 24 * 60)
        return make_public(str(self.uuid), self.filename)

    def get_file(self):
        if self.bitrix_file_id is not None and self.bitrix_file_id > 0:
            return BytesIO(get_file_content(self.bitrix_file_id))
        return get_file(str(self.uuid), self.filename)

    def delete_s3_file(self):
        if self.uuid is not None and self.bitrix_file_id is not None and self.bitrix_file_id > 0:
            result = False

            try:
                delete_file(str(self.uuid), self.filename)
                file = get_file(str(self.uuid), self.filename)
                print(file)
            except Exception as e:
                if str(e).find("NoSuchBucket") >= 0:
                    result = True
                if str(e).find("NoSuchKey") >= 0:
                    result = True
                if result is False:
                    print(traceback.format_exc())
            if result is True:
                self.is_s3_deleted = True
                db.session.commit()
        return False


class S3FileSchema(ModelSchema):

    versions = fields.Constant([])
    public_link = fields.String()

    class Meta:
        model = S3File
