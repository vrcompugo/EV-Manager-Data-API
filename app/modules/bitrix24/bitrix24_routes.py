from flask import Blueprint


from.sections.commissions import register_routes as commissions_routes
from.sections.downloads import register_routes as download_routes
from.sections.resellers import register_routes as resellers_routes
from.sections.salesportal import register_routes as salesportal_routes


bitrix24_bp = Blueprint('bitrix24', __name__, template_folder='templates')

commissions_routes(bitrix24_bp)
download_routes(bitrix24_bp)
resellers_routes(bitrix24_bp)
salesportal_routes(bitrix24_bp)


@bitrix24_bp.route("/")
def index():
    return "1.0.1"
