from app import db


class MfrExportBuffer(db.Model):
    __tablename__ = "mfr_export_buffer"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.String(200))
    last_change = db.Column(db.DateTime)
    data = db.Column(db.JSON)
