import datetime
from sqlalchemy import or_

from app import db
from app.models import UserRole, User
from app.modules.user.user_services import add_item as add_user_item
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict

from ..models.reseller import Reseller, ResellerSchema


def add_item(data):
    sales_role = db.session.query(UserRole).filter(UserRole.code == "sales").one()
    user = User.query.filter(or_(User.username == data["username"], User.email == data["email"])).first()
    if user is None:
        user = add_user_item({
            "username": data["email"],
            "password": "test",
            "email": data["email"],
            "roles": [sales_role.id]
        })
    new_item = Reseller()
    new_item = set_attr_by_dict(new_item, data, ["id"])
    new_item.user_id = user.id
    db.session.add(new_item)
    db.session.commit()
    return new_item


def update_item(id, data):
    item = db.session.query(Reseller).get(id)
    if item is not None:
        item = set_attr_by_dict(item, data, ["id"])
        db.session.commit()
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(Reseller, ResellerSchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields = None):
    return get_one_item_by_model(Reseller, ResellerSchema, id, fields, [])

