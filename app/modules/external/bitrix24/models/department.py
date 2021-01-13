from app import db


class BitrixDepartment(db.Model):
    __versioned__ = {}
    __tablename__ = "bitrix_department"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bitrix_id = db.Column(db.Integer)
    data = db.Column(db.JSON)
