from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields
from enum import Enum

from app import db
from app.basemodel import BaseModel
from app.modules.customer.models.customer import CustomerSchema
from app.modules.reseller.models.reseller import ResellerSchema


class OfferV2(BaseModel, db.Model):
    __versioned__ = {}
    __tablename__ = "offer_v2"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    customer = db.relationship("Customer")
    address_id = db.Column(db.Integer, db.ForeignKey("customer_address.id"))
    address = db.relationship("CustomerAddress")
    payment_account_id = db.Column(db.Integer, db.ForeignKey("customer_payment_account.id"))
    payment_account = db.relationship("CustomerPaymentAccount")
    reseller_id = db.Column(db.Integer, db.ForeignKey("reseller.id"))
    reseller = db.relationship("Reseller")
    lead_id = db.Column(db.Integer, db.ForeignKey("lead.id"))
    lead = db.relationship("Lead")
    survey_id = db.Column(db.Integer, db.ForeignKey("survey.id"))
    survey = db.relationship("Survey")
    is_sent = db.Column(db.Boolean)
    offer_group = db.Column(db.String(20))
    number = db.Column(db.String(40))
    datetime = db.Column(db.DateTime)
    currency = db.Column(db.String(10))
    tax_rate = db.Column(db.Integer)
    data = db.Column(db.JSON)
    calculated = db.Column(db.JSON)
    subtotal = db.Column(db.Numeric(scale=4, precision=12))
    subtotal_net = db.Column(db.Numeric(scale=4, precision=12))
    shipping_cost = db.Column(db.Numeric(scale=4, precision=12))
    shipping_cost_net = db.Column(db.Numeric(scale=4, precision=12))
    discount_total = db.Column(db.Numeric(scale=4, precision=12))
    total_tax = db.Column(db.Numeric(scale=4, precision=12))
    total = db.Column(db.Numeric(scale=4, precision=12))
    status = db.Column(db.String(20))
    last_updated = db.Column(db.DateTime)
    items = db.relationship("OfferV2Item", order_by="OfferV2Item.id")

    @hybrid_property
    def search_query(self):
        return db.session.query(OfferV2)

    @hybrid_property
    def number_prefix(self):
        suffix = ""
        if self.reseller is not None and self.reseller.document_style == "bsh":
            suffix = "BSH-"
        if self.reseller is not None and self.reseller.document_style == "eeg":
            suffix = "EEG-"
        if self.offer_group == "pv-offer":
            return suffix + "PV-"
        if self.offer_group == "cloud-offer":
            return suffix + "C-"
        if self.offer_group == "enpal-offer":
            return suffix + "EN-"
        if self.offer_group == "heater-offer":
            return suffix + "HZ-"
        if self.offer_group == "heater-offer-con":
            return suffix + "HZC-"
        if self.offer_group == "roof-offer":
            return suffix + "DA-"
        return "?"

    @hybrid_property
    def pdf(self):
        from app.models import S3File
        from ..services.pdf_generation.offer import generate_offer_pdf

        s3_file = S3File.query\
            .filter(S3File.model == "OfferV2")\
            .filter(S3File.model_id == self.id)\
            .first()
        if s3_file is None:
            if self.offer_group in ["pv-offer", "cloud-offer", "enpal-offer", "heater-offer", "roof-offer", "heater-offer-con"]:
                if self.offer_group != "pv-offer" or "pv_options" in self.survey.data:
                    generate_offer_pdf(self)
                    s3_file = S3File.query\
                        .filter(S3File.model == "OfferV2")\
                        .filter(S3File.model_id == self.id)\
                        .first()
                    if s3_file is not None:
                        return s3_file
            return None
        return s3_file

    @hybrid_property
    def cloud_pdf(self):
        from app.models import S3File
        from ..services.pdf_generation.cloud_offer import generate_cloud_pdf

        s3_file = S3File.query\
            .filter(S3File.model == "OfferV2Cloud")\
            .filter(S3File.model_id == self.id)\
            .first()
        if s3_file is None:
            if self.offer_group == "pv-offer":
                if "pv_options" in self.survey.data:
                    generate_cloud_pdf(self)
                    s3_file = S3File.query\
                        .filter(S3File.model == "OfferV2Cloud")\
                        .filter(S3File.model_id == self.id)\
                        .first()
                    if s3_file is not None:
                        return s3_file
            return None
        return s3_file

    @hybrid_property
    def feasibility_study_pdf(self):
        from app.models import S3File
        from ..services.pdf_generation.feasibility_study import generate_feasibility_study_pdf

        s3_file = S3File.query\
            .filter(S3File.model == "OfferV2FeasibilityStudy")\
            .filter(S3File.model_id == self.id)\
            .first()
        if s3_file is None:
            if self.offer_group == "pv-offer" or self.offer_group == "cloud-offer":
                if self.offer_group == "cloud-offer":
                    if self.data is None or "loan_total" not in self.data or self.data["loan_total"] == "" or self.data["loan_total"] is None:
                        return None
                generate_feasibility_study_pdf(self)
                s3_file = S3File.query\
                    .filter(S3File.model == "OfferV2FeasibilityStudy")\
                    .filter(S3File.model_id == self.id)\
                    .first()
                if s3_file is not None:
                    return s3_file
            return None
        return s3_file

    @hybrid_property
    def feasibility_study_short_pdf(self):
        from app.models import S3File
        from ..services.pdf_generation.feasibility_study import generate_feasibility_study_short_pdf

        s3_file = S3File.query\
            .filter(S3File.model == "OfferV2FeasibilityStudyShort")\
            .filter(S3File.model_id == self.id)\
            .first()
        if s3_file is None:
            if self.offer_group == "pv-offer" or self.offer_group == "cloud-offer":
                if self.offer_group == "cloud-offer":
                    if self.data is None or "loan_total" not in self.data or self.data["loan_total"] == "" or self.data["loan_total"] is None:
                        return None
                generate_feasibility_study_short_pdf(self)
                s3_file = S3File.query\
                    .filter(S3File.model == "OfferV2FeasibilityStudyShort")\
                    .filter(S3File.model_id == self.id)\
                    .first()
                if s3_file is not None:
                    return s3_file
            return None
        return s3_file


class OfferV2Schema(ModelSchema):

    versions = fields.Constant([])

    class Meta:
        model = OfferV2
