import uuid
import datetime

from app import db
from app.modules.user.models.user import User, UserSchema
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model


def add_item(data):
    user = User.query.filter_by(email=data['email']).first()
    if not user:
        new_user = User(
            public_id=str(uuid.uuid4()),
            email=data['email'],
            username=data['username'],
            password=data['password'],
            registered_on=datetime.datetime.utcnow()
        )
        save_changes(new_user)
        return new_user
    else:
        raise ApiException("item_already_exists", "User already exists.", 409)


def update_item(public_id, data):
    user = User.query.filter_by(public_id=public_id).first()
    if user is not None:
        user.email=data['email']
        user.username=data['username']
        user.password=data['password']
        save_changes(user)
        response_object = {
            'status': 'success',
            'message': 'Successfully updated.'
        }
        return response_object, 201
    else:
        response_object = {
            'status': 'error',
            'message': "User doesn't exist.",
        }
        return response_object, 409


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(User, UserSchema, tree, sort, offset, limit, fields)


def get_one_item(public_id):
    return User.query.filter_by(public_id=public_id).first()


def save_changes(data):
    db.session.add(data)
    db.session.commit()
