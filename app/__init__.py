import jinja2
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from sqlalchemy_continuum import make_versioned
from sqlalchemy_continuum.plugins import FlaskPlugin
from sqlalchemy.orm import sessionmaker

from .config import config_by_name
from .utils.jinja_filters import apply_filters

db = SQLAlchemy()
flask_bcrypt = Bcrypt()
make_versioned(user_cls=None, plugins=[FlaskPlugin()])


def create_app(config_name):
    from flask_cors import CORS
    app = Flask(__name__)
    my_loader = jinja2.ChoiceLoader([
        app.jinja_loader,
        jinja2.FileSystemLoader('app/modules/offer/templates/'),
    ])
    app.jinja_loader = my_loader
    app.config.from_object(config_by_name[config_name])
    db.init_app(app)
    flask_bcrypt.init_app(app)
    apply_filters(app)
    CORS(app, origins="*", allow_headers=[
        "Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
        supports_credentials=True)

    return app
