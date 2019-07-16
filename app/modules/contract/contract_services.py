import datetime
import random

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.modules.project.project_services import add_item as add_project
from app.models import Offer

from .models.contract import Contract, ContractSchema


def add_item(data):
    offer = None
    if data["offer_id"] is not None:
        offer = db.session.query(Offer).get(data["offer_id"])
    if offer is not None:
        data["customer_id"] = offer.customer_id
        data["address_id"] = offer.address_id
        data["payment_account_id"] = offer.payment_account_id
        data["reseller_id"] = offer.reseller_id
    project = add_project({
        "customer_id": data["customer_id"],
        "address_id": data["address_id"],
        "payment_account_id": data["payment_account_id"],
        "reseller_id": data["reseller_id"],
        "datetime": data["datetime"]
    })
    data["project_id"] = project.id
    new_item = Contract()
    new_item = set_attr_by_dict(new_item, data, ["id"])
    new_item.number = "C{}".format(random.randint(100000, 999999))
    db.session.add(new_item)
    db.session.commit()
    return new_item


def update_item(id, data):
    item = db.session.query(Contract).get(id)
    if item is not None:
        item = set_attr_by_dict(item, data, ["id"])
        db.session.commit()
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(Contract, ContractSchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields = None):
    return get_one_item_by_model(Contract, ContractSchema, id, fields, [])

