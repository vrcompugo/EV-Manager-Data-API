import os
from flask_restplus import Api, apidoc
from flask import Blueprint, Response, url_for, send_from_directory
from flask_httpauth import HTTPBasicAuth

from app.modules.auth.auth_routes import api as auth_ns
from app.modules.cloud.routes import api as cloud_ns
from app.modules.customer.routes import api as customer_ns
from app.modules.file.file_routes import api as file_ns
from app.modules.importer.import_routes import api as import_ns
from app.modules.lead.lead_routes import api as lead_ns
from app.modules.offer.offer_routes import api as offer_ns
from app.modules.order.order_routes import api as order_ns
from app.modules.reseller.routes.reseller_group_routes import api as reseller_group_ns
from app.modules.reseller.routes.reseller_routes import api as reseller_ns
from app.modules.survey.survey_routes import api as survey_ns
from .modules.auth.auth_decorators import full_permission_list

auth = HTTPBasicAuth()
blueprint = Blueprint('api', __name__)

authorizations = {
    'jwt': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization'
    }
}
full_permission_list = [x for x in full_permission_list if x is not None]


class MyApi(Api):
    @property
    def specs_url(self):
        """Monkey patch for HTTPS"""
        env = os.getenv('ENVIRONMENT') or 'dev'
        scheme = 'https'
        return url_for(self.endpoint('specs'), _external=True, _scheme=scheme)


api = MyApi(
    blueprint,
    doc=None,
    title='EV-Manager Data API',
    contact="hb&b Werbeagentur und Unternehmensberatung-GmbH",
    contact_url="https://www.hbb-werbung.de",
    contact_email="info@hbb-werbung.de",
    version='1.0.0',
    security=["jwt"],
    authorizations=authorizations
)


@auth.get_password
def get_pw(username):
    if username == "dev":
        return "dev"
    return None


@api.documentation
@blueprint.route("/doc")
@auth.login_required
def custom_ui():
    return apidoc.ui_for(api)


@blueprint.route("/")
def version_number():
    return Response('{"version":"1.0.0"}', mimetype='application/json')


api.add_namespace(cloud_ns, path='/cloud')
api.add_namespace(customer_ns, path='/customers')
api.add_namespace(reseller_ns, path='/resellers')
api.add_namespace(reseller_group_ns, path='/reseller_groups')
api.add_namespace(survey_ns, path='/surveys')
api.add_namespace(file_ns, path='/files')
api.add_namespace(import_ns, path='/imports')
api.add_namespace(lead_ns, path='/leads')
api.add_namespace(offer_ns, path='/offers')
api.add_namespace(order_ns, path='/orders')
api.add_namespace(auth_ns, path='/auth')


def register_blueprints(app):
    from app.modules.bitrix24.bitrix24_routes import bitrix24_bp
    from app.modules.cloud.cloud2_routes import blueprint as cloud2_bp
    from app.modules.fakturia.routes import blueprint as fakturia_bp
    from app.modules.invoice.invoice_routes import blueprint as invoice_bp
    from app.modules.quote_calculator.routes import blueprint as quote_calculator_bp
    from app.modules.external.enbw.routes import blueprint as enbw_bp
    from app.modules.sign.sign_routes import blueprint as sign_bp
    from app.modules.order_confirmation.routes import blueprint as order_confirmation_bp
    from app.modules.user.user_routes import blueprint as users_bp
    app.register_blueprint(blueprint)
    app.register_blueprint(bitrix24_bp, url_prefix="/bitrix24")
    app.register_blueprint(users_bp, url_prefix="/users")
    app.register_blueprint(cloud2_bp, url_prefix="/cloud2")
    app.register_blueprint(fakturia_bp, url_prefix="/fakturia")
    app.register_blueprint(invoice_bp, url_prefix="/invoice")
    app.register_blueprint(quote_calculator_bp, url_prefix="/quote_calculator")
    app.register_blueprint(enbw_bp, url_prefix="/enbw")
    app.register_blueprint(sign_bp, url_prefix="/sign")
    app.register_blueprint(order_confirmation_bp, url_prefix="/order_confirmation")
