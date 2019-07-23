import datetime
import uuid

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict

from .models.s3_file import S3File, S3FileSchema
from .minio import put_file


def add_item(data):
    new_item = S3File()
    new_item = set_attr_by_dict(new_item, data, ["id", "file"])
    if "uuid" not in data or data["uuid"] is None or len(data["uuid"]) < 10:
        new_item.uuid = uuid.uuid4()
    new_item.uploaded = datetime.datetime.now()
    db.session.add(new_item)
    db.session.commit()
    put_file(str(new_item.uuid), new_item.filename, data)

    return new_item


def update_item(id, data):
    item = db.session.query(S3File).get(id)
    if item is not None:
        if "uuid" not in data or data["uuid"] is None or len(data["uuid"]) < 10:
            item.uuid = uuid.uuid4()
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


def get_one_item(id, fields = None):
    return get_one_item_by_model(S3File, S3FileSchema, id, fields)

