from app import db


class CustomerAddress(db.Model):
    __versioned__ = {}
    __tablename__ = "customer_address"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer(), db.ForeignKey('customer.id'))
    salutation = db.Column(db.String(30))
    title = db.Column(db.String(30))
    firstname = db.Column(db.String(100))
    lastname = db.Column(db.String(100))
    company = db.Column(db.String(100))
    street = db.Column(db.String(100))
    street_nb = db.Column(db.String(80))
    street_extra = db.Column(db.String(50))
    zip = db.Column(db.String(20))
    city = db.Column(db.String(60))
    status = db.Column(db.String(30))
