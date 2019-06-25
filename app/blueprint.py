from flask_restplus import Api, apidoc
from flask import Blueprint, Response
from flask_httpauth import HTTPBasicAuth

from app.modules.user.user_routes import api as user_ns
from app.modules.customer.routes import api as customer_ns
from app.modules.auth.auth_routes import api as auth_ns

auth = HTTPBasicAuth()
blueprint = Blueprint('api', __name__)

authorizations = {
    'jwt': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization'
    }
}

api = Api(blueprint,
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

api.add_namespace(user_ns, path='/users')
api.add_namespace(customer_ns, path='/customers')
api.add_namespace(auth_ns, path='/auth')