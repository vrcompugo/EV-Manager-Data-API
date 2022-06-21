import datetime
import uuid
import jwt
import time

from sqlalchemy import or_

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict

from .models.s3_file import S3File, S3FileSchema
from .minio import put_file
from app.modules.external.bitrix24.drive import add_file, create_folder_path, get_file_content


key = "0u9cQU8YNmUSAgIuq7MaBKh7YpE4z1ZO"


def add_item(data):
    new_item = S3File()
    new_item = set_attr_by_dict(new_item, data, ["id", "file"])
    if "uuid" not in data or data["uuid"] is None or len(data["uuid"]) < 10:
        new_item.uuid = str(uuid.uuid4())
    new_item.uploaded = datetime.datetime.now()
    print("add file1")
    if 'folder_id' in data:
        folder_id = data['folder_id']
    else:
        if 'prepend_path' not in data:
            folder_id = create_folder_path(446126, f"{new_item.uuid}")
        else:
            folder_id = create_folder_path(446126, f"{data['prepend_path']}")
    print("add file2")
    bitrix_file_id = add_file(folder_id, data)
    print("add file3")
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
        print("update file")
        if 'folder_id' in data:
            folder_id = data['folder_id']
        else:
            if 'prepend_path' not in data:
                folder_id = create_folder_path(446126, f"{item.uuid}")
            else:
                folder_id = create_folder_path(446126, f"{data['prepend_path']}")
        print("update file2")
        if item.bitrix_file_id is not None:
            data["bitrix_file_id"] = item.bitrix_file_id
        bitrix_file_id = add_file(folder_id, data)
        print("update file3")
        if bitrix_file_id is None:
            raise ApiException("upload-failed", "file upload failed", 500)
        item.bitrix_file_id = bitrix_file_id
        db.session.commit()
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def cron_bitrix_export_item():
    items = db.session.query(S3File).filter(S3File.bitrix_file_id > 0).filter(or_(S3File.is_s3_deleted.is_(None), S3File.is_s3_deleted.is_(False))).order_by(S3File.uploaded.asc()).limit(1000).all()
    for index, item in enumerate(items):
        content = get_file_content(item.bitrix_file_id)
        if len(content) > 1000:
            print(item.id)
            item.delete_s3_file()
            time.sleep(2)


def bitrix_export_item(item):
    if item is not None and item.bitrix_file_id is None:
        try:
            file_content = item.get_file()
        except Exception as e:
            return None
        file_content = file_content.read()
        data = {
            "filename": item.filename,
            "file_content": file_content
        }
        print("update file")
        folder_id = create_folder_path(446126, f"{item.uuid}")
        print("update file2")
        bitrix_file_id = add_file(folder_id, data)
        print("update file3")
        print(bitrix_file_id)
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
