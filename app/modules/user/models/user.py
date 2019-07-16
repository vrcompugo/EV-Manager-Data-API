from app import db, flask_bcrypt
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import Schema, fields

from .user_role import UserRoleSchema


association_table = db.Table('user_role_association',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('user_role_id', db.Integer, db.ForeignKey('user_role.id'))
)


class User(db.Model):
    """ User Model for storing user related details """
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    registered_on = db.Column(db.DateTime, nullable=False)
    username = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(100))
    roles = db.relationship("UserRole", secondary=association_table, backref="users")

    @property
    def password(self):
        raise AttributeError('password: write-only field')

    @password.setter
    def password(self, password):
        self.password_hash = flask_bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return flask_bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return "<User '{}'>".format(self.username)





class UserSchema(ModelSchema):

    roles = fields.Nested(UserRoleSchema, many=True)
    password_hash = fields.Constant("")
    versions = fields.Constant([])

    class Meta:
        model = User
