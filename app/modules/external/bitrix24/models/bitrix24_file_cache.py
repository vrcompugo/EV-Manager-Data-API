from app import db

class Bitrix24FileCache(db.Model):
    __tablename__ = "bitrix24_file_cache"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    drive_id = db.Column(db.String(30))
    datetime = db.Column(db.DateTime)
    is_static = db.Column(db.Boolean)
    content = db.Column(db.LargeBinary)
