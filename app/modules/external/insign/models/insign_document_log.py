from datetime import datetime
from app import db


class InsignDocumentLog(db.Model):
    __tablename__ = "insign_document_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(120))
    docid = db.Column(db.String(100))
    data = db.Column(db.JSON)
