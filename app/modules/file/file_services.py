import datetime
import uuid
import jwt

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict

from .models.s3_file import S3File, S3FileSchema
from .minio import put_file
from app.modules.external.bitrix24.drive import add_file, create_folder_path


key = "0u9cQU8YNmUSAgIuq7MaBKh7YpE4z1ZO"


def add_item(data):
    new_item = S3File()
    new_item = set_attr_by_dict(new_item, data, ["id", "file"])
    if "uuid" not in data or data["uuid"] is None or len(data["uuid"]) < 10:
        new_item.uuid = str(uuid.uuid4())
    new_item.uploaded = datetime.datetime.now()
    if 'prepend_path' not in data:
        data['prepend_path'] = ""
    folder_id = create_folder_path(442866, f"{data['prepend_path']}{new_item.uuid}")
    bitrix_file_id = add_file(folder_id, data)
    if bitrix_file_id is None:
        raise ApiException("upload-failed", "file upload failed", 500)
    new_item.bitrix_file_id = bitrix_file_id
    db.session.add(new_item)
    db.session.commit()

    return new_item


def update_item(id, data):
    item = db.session.query(S3File).get(id)
    if item is not None:
        item.uuid = str(uuid.uuid4())
        item = set_attr_by_dict(item, data, ["id", "file"])
        if 'prepend_path' not in data:
            data['prepend_path'] = ""
        folder_id = create_folder_path(442866, f"{data['prepend_path']}{item.uuid}")
        bitrix_file_id = add_file(folder_id, data)
        if bitrix_file_id is None:
            raise ApiException("upload-failed", "file upload failed", 500)
        item.bitrix_file_id = bitrix_file_id
        db.session.commit()
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def sync_item(data):
    item = None
    if "uuid" in data and data["uuid"] is not None and len(data["uuid"]) > 8:
        item = db.session.query(S3File).filter(S3File.uuid == data["uuid"]).first()
    if item is None:
        return add_item(data)
    else:
        return update_item(item.id, data)


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(S3File, S3FileSchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields=None):
    return get_one_item_by_model(S3File, S3FileSchema, id, fields)


def encode_file_token(id, days=90):
    try:
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=days),
            'iat': datetime.datetime.utcnow(),
            'id': id
        }
        return jwt.encode(
            payload,
            key,
            algorithm='HS256'
        )
    except Exception as e:
        return e


def decode_file_token(token):
    return jwt.decode(token, key)
