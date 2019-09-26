from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.modules.file.file_services import add_item as add_file, S3File, S3FileSchema

from ..models import Customer, CustomerSchema, CustomerAddress, CustomerPaymentAccount


def add_item(data):
    item = None
    print(data)
    if int(data["customer_id"]) == 0:
        if "customer_number" in data and len(str(data["customer_number"]))>0:
            item = Customer.query.filter(Customer.customer_number == data["customer_number"]).first()
        if item is None and "lead_number" in data and len(str(data["lead_number"]))>0:
            item = Customer.query.filter(Customer.lead_number == data["lead_number"]).first()
    else:
        item = Customer.query.filter(Customer.id == data["customer_id"]).first()
    if item is not None:
        data["model"] = "customer"
        data["model_id"] = item.id
        data["filename"] = data["type"] + "/" + data["filename"]
        new_item = add_file(data)
        return new_item
    else:
        raise ApiException("item_not_found", "Customer not found.", 404)


def update_item(id, data):
    item = db.session.query(S3File).get(id)
    if item is not None:
        item = set_attr_by_dict(item, data, ["id"])
        db.session.commit()
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 404)


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(S3File, S3FileSchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields = None):
    return get_one_item_by_model(S3File, S3FileSchema, id, fields)

