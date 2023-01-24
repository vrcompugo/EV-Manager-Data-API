from app import db
from app.basemodel import BaseModel
from sqlalchemy.dialects.postgresql import JSONB


class ENBWContractHistory(BaseModel, db.Model):
    __tablename__ = "enbw_contract_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    enbw_contract_id = db.Column(db.Integer(), db.ForeignKey('enbw_contract.id'))
    datetime = db.Column(db.DateTime)
    action = db.Column(db.String(120))
    post_data = db.Column(JSONB)
    api_response_status = db.Column(db.String(20))
    api_response = db.Column(JSONB)
    api_response_raw = db.Column(db.Text())
