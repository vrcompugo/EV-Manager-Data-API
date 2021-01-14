from app import db


class BitrixDriveFolder(db.Model):
    __versioned__ = {}
    __tablename__ = "bitrix_folder"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bitrix_id = db.Column(db.Integer)
    parent_folder_id = db.Column(db.Integer)
    path = db.Column(db.String(250))
    data = db.Column(db.JSON)
