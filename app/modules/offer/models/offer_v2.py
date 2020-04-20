from sqlalchemy.ext.hybrid import hybrid_property
from marshmallow_sqlalchemy import ModelSchema
from marshmallow import fields
from enum import Enum

from app import db
from app.modules.customer.models.customer import CustomerSchema
from app.modules.reseller.models.reseller import ResellerSchema


class OfferV2(db.Model):
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
    offer_group = db.Column(db.String(20))
    datetime = db.Column(db.DateTime)
    currency = db.Column(db.String(10))
    tax_rate = db.Column(db.Integer)
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
    def pdf(self):
        from app.models import S3File
        from ..services.pdf_generation.pv_offer import generate_pv_offer_pdf

        if self.id < 1497:
            return None
        s3_file = S3File.query\
            .filter(S3File.model == "OfferV2")\
            .filter(S3File.model_id == self.id)\
            .first()
        if s3_file is None:
            if self.offer_group == "pv-offer":
                generate_pv_offer_pdf(self)
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
        if self.id < 1497:
            return None
        s3_file = S3File.query\
            .filter(S3File.model == "OfferV2Cloud")\
            .filter(S3File.model_id == self.id)\
            .first()
        if s3_file is None:
            if self.offer_group == "pv-offer":
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

        if self.id < 1497:
            return None
        s3_file = S3File.query\
            .filter(S3File.model == "OfferV2FeasibilityStudy")\
            .filter(S3File.model_id == self.id)\
            .first()
        if s3_file is None:
            if self.offer_group == "pv-offer":
                generate_feasibility_study_pdf(self)
                s3_file = S3File.query\
                    .filter(S3File.model == "OfferV2FeasibilityStudy")\
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
