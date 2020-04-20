from flask import Blueprint


from.sections.calendar import register_routes as calendar_routes
from.sections.commissions import register_routes as commissions_routes
from.sections.downloads import register_routes as download_routes
from.sections.dresdner_bank import register_routes as dresdner_routes
from.sections.resellers import register_routes as resellers_routes
from.sections.salesportal import register_routes as salesportal_routes
from.sections.settings import register_routes as settings_routes


bitrix24_bp = Blueprint('bitrix24', __name__, template_folder='templates')

calendar_routes(bitrix24_bp)
commissions_routes(bitrix24_bp)
download_routes(bitrix24_bp)
dresdner_routes(bitrix24_bp)
resellers_routes(bitrix24_bp)
salesportal_routes(bitrix24_bp)
settings_routes(bitrix24_bp)


@bitrix24_bp.route("/")
def index():
    return "1.0.1"
