from app import db
from app.basemodel import BaseModel
from sqlalchemy.dialects.postgresql import JSONB


class ENBWContract(BaseModel, db.Model):
    __tablename__ = "enbw_contract"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    main_contract_number = db.Column(db.String(120))
    sub_contract_number = db.Column(db.String(120))
    deal_id = db.Column(db.Integer)
    enbw_contract_number = db.Column(db.String(50))
    joulesId = db.Column(db.String(50))
    tarif_data = db.Column(db.JSON)
    status = db.Column(db.String(50))
    status_message = db.Column(db.String(250))
    histories = db.relationship("ENBWContractHistory", order_by="desc(ENBWContractHistory.id)")
