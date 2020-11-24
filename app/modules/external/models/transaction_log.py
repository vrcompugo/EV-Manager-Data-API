from app import db


class TransactionLog(db.Model):
    __tablename__ = "transaction_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    domain = db.Column(db.String(40))
    source = db.Column(db.String(40))
    model = db.Column(db.String(60))
    unique_identifier = db.Column(db.String(120))
