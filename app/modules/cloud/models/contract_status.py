from sqlalchemy.dialects.postgresql import JSONB

from app import db


class ContractStatus(db.Model):
    __tablename__ = "contract_status"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    contract_number = db.Column(db.String(50))
    year = db.Column(db.String(10))
    has_lightcloud = db.Column(db.Boolean)
    has_cloud_number = db.Column(db.Boolean)
    cloud_number = db.Column(db.String(80))
    has_begin_date = db.Column(db.Boolean)
    has_smartme_number = db.Column(db.Boolean)
    has_smartme_number_values = db.Column(db.Boolean)
    has_smartme_number_heatcloud = db.Column(db.Boolean)
    has_smartme_number_heatcloud_values = db.Column(db.Boolean)
    has_correct_usage = db.Column(db.String(80))
    has_sherpa_values = db.Column(db.Boolean)
    has_heatcloud = db.Column(db.Boolean)
    has_ecloud = db.Column(db.Boolean)
    has_consumers = db.Column(db.Boolean)
    has_emove = db.Column(db.Boolean)
    pdf_file_id = db.Column(db.Integer)
    pdf_file_link = db.Column(db.String(250))
    to_pay = db.Column(db.Numeric(scale=4, precision=12))
    is_generated = db.Column(db.Boolean)
    is_fakturia = db.Column(db.Boolean)
    is_fakturia_transfered = db.Column(db.Boolean)
    is_invoiced = db.Column(db.Boolean)
    manuell_data = db.Column(JSONB)
    status = db.Column(db.String(150))
