import json
import os
from flask import Blueprint, request, render_template, make_response
from sqlalchemy import func

from app import db
from app.exceptions import ApiException
from app.decorators import api_response
from app.modules.auth import get_auth_info
from app.modules.auth.jwt_parser import encode_jwt

from .models.invoice_bundle import InvoiceBundle


blueprint = Blueprint("invoice", __name__, template_folder='templates')


@blueprint.route("/bundles", methods=['GET'])
@api_response
def get_bundles_list():
    auth_info = get_auth_info()
    if auth_info is None or auth_info["domain_raw"] != "keso.bitrix24.de":
        return {"status": "failed", "data": {}, "message": "auth failed"}

    sql = InvoiceBundle.query

    limit = 100
    page = 1
    sort_by = ["kw"]
    sort_desc = [True]
    if request.args.get("per_page") in ["100", "200", "300"]:
        limit = int(request.args.get("per_page"))
    if request.args.get("page") not in [None, ""]:
        page = int(request.args.get("page"))
    if request.args.get("sort_by[]") not in [None, ""]:
        sort_by = [request.args.get("sort_by[]")]
    if request.args.get("sort_desc[]") in ["true", "false"]:
        sort_desc = [request.args.get("sort_desc[]") == "true"]

    total = get_count(sql)
    order_by_list = []
    for i, col in enumerate(sort_by):
        if hasattr(InvoiceBundle, col):
            if i < len(sort_desc) and sort_desc[i] is True:
                if col == "kw":
                    order_by_list.append(getattr(InvoiceBundle, "year").desc())
                order_by_list.append(getattr(InvoiceBundle, col).desc())
            else:
                if col == "kw":
                    order_by_list.append(getattr(InvoiceBundle, "year").asc())
                order_by_list.append(getattr(InvoiceBundle, col).asc())
    order_by_list.append(InvoiceBundle.id.desc())
    sql = sql.order_by(*order_by_list)
    print(sql)
    transactions = sql.offset((page - 1) * limit).limit(limit).all()
    items = []
    for transaction in transactions:
        items.append(transaction.to_dict())

    return {"status": "success", "data": {"items": items, "total": total}}


def get_count(q):
    count_q = q.statement.with_only_columns([func.count()]).order_by(None)
    count = q.session.execute(count_q).scalar()
    return count


@blueprint.route("/index", methods=['GET', 'POST'])
def invoice_index():
    auth_info = get_auth_info()
    if auth_info["user"] is None:
        return "Forbidden"
    token = encode_jwt(auth_info, expire_minutes=600)
    return render_template("invoice/invoice.html", token=token)


@blueprint.route("/install", methods=['GET', 'POST'])
def install_invoice():
    env = os.getenv('ENVIRONMENT')
    return render_template("invoice/install.html", domain=request.host, env=env)


@blueprint.route("/uninstall", methods=['POST'])
def uninstall_invoice():
    return render_template("invoice/uninstall.html", domain=request.host)
