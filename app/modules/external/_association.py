import sys

from app import db
from flask import request
from app.modules.external.models.transaction_log import TransactionLog


def get_domain(domain_raw=None):
    if domain_raw is None and request.host_url == "http://localhost/":
        domain_raw = "keso.bitrix24.de"
    return domain_raw


def find_log(source, model, identifier, domain_raw=None):
    domain = get_domain(domain_raw)
    query = db.session.query(TransactionLog)\
        .filter(TransactionLog.domain == domain)\
        .filter(TransactionLog.source == source)\
        .filter(TransactionLog.model == model)\
        .filter(TransactionLog.unique_identifier == str(identifier))
    return query.first()


def log_item(source, model, identifier, domain_raw=None):
    domain = get_domain(domain_raw)
    item = find_log(source, model, identifier, domain)
    if item is None:
        item = TransactionLog(
            source=source,
            model=model,
            unique_identifier=str(identifier),
            domain=domain
        )
        db.session.add(item)
        db.session.commit()
