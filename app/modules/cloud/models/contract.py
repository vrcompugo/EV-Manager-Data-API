from app import db


class Contract(db.Model):
    __tablename__ = "contract2"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    contract_number = db.Column(db.String(50))
    begin = db.Column(db.DateTime)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    street = db.Column(db.String(50))
    street_nb = db.Column(db.String(50))
    zip = db.Column(db.String(50))
    city = db.Column(db.String(50))
