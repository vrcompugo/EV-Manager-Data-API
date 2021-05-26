from app import db


class UserCache(db.Model):
    __tablename__ = "user_cache"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bitrix_id = db.Column(db.Integer)
    email = db.Column(db.String(250))
    department = db.Column(db.String(250))
    data = db.Column(db.JSON)
    last_update = db.Column(db.DateTime)
