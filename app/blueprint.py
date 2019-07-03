import os
from flask_restplus import Api, apidoc
from flask import Blueprint, Response, url_for
from flask_httpauth import HTTPBasicAuth

from app.modules.auth.auth_routes import api as auth_ns
from app.modules.contract.contract_routes import api as contract_ns
from app.modules.customer.routes import api as customer_ns
from app.modules.offer.offer_routes import api as offer_ns
from app.modules.product.product_routes import api as product_ns
from app.modules.project.project_routes import api as project_ns
from app.modules.pv_system.pv_system_routes import api as pv_system_ns
from app.modules.reseller.routes.reseller_group_routes import api as reseller_group_ns
from app.modules.reseller.routes.reseller_routes import api as reseller_ns
from app.modules.survey.survey_routes import api as survey_ns
from app.modules.task.task_routes import api as task_ns
from app.modules.user.user_routes import api as user_ns, api2 as user_role_ns
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
        scheme = 'http' if env == "dev" else 'https'
        return url_for(self.endpoint('specs'), _external=True, _scheme=scheme)


api = MyApi(blueprint,
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
api.add_namespace(user_role_ns, path='/user_roles')
api.add_namespace(customer_ns, path='/customers')
api.add_namespace(reseller_ns, path='/resellers')
api.add_namespace(reseller_group_ns, path='/reseller_groups')
api.add_namespace(survey_ns, path='/surveys')
api.add_namespace(project_ns, path='/projects')
api.add_namespace(offer_ns, path='/offers')
api.add_namespace(contract_ns, path='/contracts')
api.add_namespace(product_ns, path='/product')
api.add_namespace(pv_system_ns, path='/pv_system')
api.add_namespace(task_ns, path='/tasks')
api.add_namespace(auth_ns, path='/auth')
