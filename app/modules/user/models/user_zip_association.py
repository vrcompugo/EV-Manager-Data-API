from app import db
from sqlalchemy.dialects.postgresql import JSONB


class UserZipAssociation(db.Model):
    __tablename__ = "user_zip_association"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer)
    supervisor_id = db.Column(db.Integer)
    last_assigned = db.Column(db.DateTime)
    current_cycle_index = db.Column(db.Integer)
    current_cycle_count = db.Column(db.Integer)
    max_leads = db.Column(db.Integer)
    data = db.Column(JSONB)
    user_type = db.Column(db.String(90))
    comment = db.Column(db.String(90))
