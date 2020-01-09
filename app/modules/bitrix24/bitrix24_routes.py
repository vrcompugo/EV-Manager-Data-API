from flask import Blueprint


from.sections.downloads import register_routes as download_routes
from.sections.salesportal import register_routes as salesportal_routes


bitrix24_bp = Blueprint('bitrix24', __name__, template_folder='templates')

download_routes(bitrix24_bp)
salesportal_routes(bitrix24_bp)


@bitrix24_bp.route("/")
def index():
    return "1.0.1"
