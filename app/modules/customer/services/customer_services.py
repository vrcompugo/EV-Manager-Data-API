from sqlalchemy import or_

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict

from ..models import Customer, CustomerSchema, CustomerAddress, CustomerPaymentAccount


def add_item(data):
    item = None
    if data['email'] is not None:
        item = Customer.query.filter_by(email=data['email']).first()
    if item is None and data['customer_number'] is not None:
        item = Customer.query.filter_by(customer_number=data['customer_number']).first()
    if item is None and data['lead_number'] is not None:
        item = Customer.query.filter_by(lead_number=data['lead_number']).first()
    if item is None:
        new_item = Customer()
        new_item = set_attr_by_dict(new_item, data, ["id", "default_address", "default_payment_account"])
        db.session.add(new_item)
        db.session.flush()
        if "default_address" in data:
            customer_address = CustomerAddress(**data["default_address"])
            customer_address.customer_id = new_item.id
            customer_address.status = "ok"
            new_item.default_address = customer_address
            if "default_payment_account" in data:
                default_payment_account = CustomerPaymentAccount(**data["default_payment_account"])
                default_payment_account.customer_id = new_item.id
                default_payment_account.address = customer_address
                new_item.default_payment_account = default_payment_account
        db.session.add(new_item)
        db.session.commit()
        return new_item
    else:
        raise ApiException("item_already_exists", "Item already exists.", 409)


def update_item(id, data):
    item = db.session.query(Customer).get(id)
    if item is not None:
        item = set_attr_by_dict(item, data, ["id"])
        db.session.commit()
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 404)


def merge_items(data):
    item = None
    if data['email'] is not None and data['email'] != "":
        item = Customer.query.filter(Customer.email == data['email']).first()
    if item is None and data['customer_number'] is not None and data['customer_number'] != "":
        item = Customer.query.filter(Customer.customer_number == data['customer_number']).first()
    if item is None and data['lead_number'] is not None and data['lead_number'] != "":
        item = Customer.query.filter(Customer.lead_number == data['lead_number']).first()

    if item is None:
        item = add_item(data)
    else:
        item = set_attr_by_dict(item, data, ["id"], merge=True)
        db.session.commit()
    return item


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(Customer, CustomerSchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields = None):
    return get_one_item_by_model(Customer, CustomerSchema, id, fields)

