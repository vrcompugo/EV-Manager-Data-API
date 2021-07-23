from app import db


class MfrLogEvent(db.Model):
    __tablename__ = "mfr_log_event"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_request_id = db.Column(db.String(200))
    last_change = db.Column(db.DateTime)
    processed = db.Column(db.Boolean)
