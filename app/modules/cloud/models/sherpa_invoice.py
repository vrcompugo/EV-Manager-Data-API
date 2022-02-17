from app import db


class SherpaInvoice(db.Model):
    __tablename__ = "sherpa_invoice"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    identnummer = db.Column(db.String(50))
    rechnungsnummer = db.Column(db.String(60))
    abrechnungszeitraum_von = db.Column(db.DateTime)
    abrechnungszeitraum_bis = db.Column(db.DateTime)
    zahlernummer = db.Column(db.String(60))
    abrechnungsart = db.Column(db.String(60))
    verbrauch = db.Column(db.Integer)
    tage = db.Column(db.Integer)
