from sqlalchemy.dialects.postgresql import JSONB

from app import db


class Contract(db.Model):
    __tablename__ = "contract2"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    contract_number = db.Column(db.String(50))
    main_contract_number = db.Column(db.String(50))
    deal_id = db.Column(db.Integer)
    begin = db.Column(db.DateTime)
    end = db.Column(db.DateTime)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    street = db.Column(db.String(50))
    street_nb = db.Column(db.String(50))
    zip = db.Column(db.String(50))
    city = db.Column(db.String(50))
    data = db.Column(JSONB)
