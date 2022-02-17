from app import db


class SherpaInvoiceItem(db.Model):
    __tablename__ = "sherpa_invoice_item"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sherpa_invoice_id = db.Column(db.Integer, db.ForeignKey("sherpa_invoice.id"))
    zahlernummer = db.Column(db.String(60))
    art_des_zahlerstandes = db.Column(db.String(60))
    zahlerart = db.Column(db.String(60))
    stand_alt = db.Column(db.Integer)
    datum_stand_alt = db.Column(db.DateTime)
    ablesegrund = db.Column(db.String(60))
    stand_neu = db.Column(db.Integer)
    datum_stand_neu = db.Column(db.DateTime)
    verbrauch = db.Column(db.Integer)
    tage = db.Column(db.Integer)
    wandlerfaktor = db.Column(db.String(60))
