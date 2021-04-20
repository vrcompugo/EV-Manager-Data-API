from app import db


class MfrImportBuffer(db.Model):
    __tablename__ = "mfr_import_buffer"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_request_id = db.Column(db.String(200))
    last_change = db.Column(db.DateTime)
    data = db.Column(db.JSON)
