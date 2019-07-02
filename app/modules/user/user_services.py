from sqlalchemy import or_
import datetime

from app import db
from app.modules.user.models.user import User, UserSchema
from app.modules.user.models.user_role import UserRole, UserRoleSchema
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict


def add_item(data):
    new_item = User.query.filter(or_(User.username == data["username"], User.email == data["email"])).first()
    if new_item is None:
        new_item = User()
        new_item = set_attr_by_dict(new_item, data, ["id", "registered_on", "roles"])
        new_item.password = data["password"]
        new_item.registered_on = datetime.datetime.utcnow()
        roles = []
        for role_id in data["roles"]:
            role = db.session.query(UserRole).get(role_id)
            roles.append(role)
        new_item.roles = roles
        db.session.add(new_item)
        db.session.commit()
        return new_item
    else:
        raise ApiException("item_already_exists", "User already exists.", 409)


def update_item(id, data):
    user = db.session.query(User).get(id)
    if user is not None:
        user.email=data['email']
        user.username=data['username']
        user.password=data['password']
        roles = []
        for role_id in data["roles"]:
            role = db.session.query(UserRole).get(role_id)
            roles.append(role)
        user.roles = roles
        db.session.commit()
        return user
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(User, UserSchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields = None):
    data = get_one_item_by_model(User, UserSchema, id, fields, [db.subqueryload("roles")])
    del data["password_hash"]
    return data


def get_role_items():
    roles = UserRole.query.all()
    item_schema = UserRoleSchema()
    return item_schema.dump(roles, many=True).data
