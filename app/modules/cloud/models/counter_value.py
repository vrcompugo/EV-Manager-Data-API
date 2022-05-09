from app import db


class CounterValue(db.Model):
    __tablename__ = "counter_value"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    number = db.Column(db.String(50))
    date = db.Column(db.DateTime)
    value = db.Column(db.Integer)
    origin = db.Column(db.String(50))
