from app import db, flask_bcrypt
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import Schema, fields
from sqlalchemy.ext.hybrid import hybrid_property

from .user_role import UserRoleSchema


association_table = db.Table(
    'user_role_association',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('user_role_id', db.Integer, db.ForeignKey('user_role.id'))
)


class User(db.Model):
    """ User Model for storing user related details """
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(150))
    registered_on = db.Column(db.DateTime, nullable=False)
    username = db.Column(db.String(50), unique=True)
    password_hash = db.Column(db.String(100))
    bitrix_user_id = db.Column(db.String(50))
    bitrix_department = db.Column(db.String(250))
    bitrix_department_ids = db.Column(db.JSON)
    access_key = db.Column(db.String(150))
    active = db.Column(db.Boolean)
    roles = db.relationship("UserRole", secondary=association_table, backref="users")

    @property
    def password(self):
        raise AttributeError('password: write-only field')

    @password.setter
    def password(self, password):
        self.password_hash = flask_bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return flask_bcrypt.check_password_hash(self.password_hash, password)

    @hybrid_property
    def search_query(self):
        return db.session.query(User)

    @hybrid_property
    def fulltext(self):
        return User.name

    def __repr__(self):
        return "<User '{}'>".format(self.username)


class UserSchema(ModelSchema):

    roles = fields.Nested(UserRoleSchema, many=True)
    password_hash = fields.Constant("")
    versions = fields.Constant([])

    class Meta:
        model = User
