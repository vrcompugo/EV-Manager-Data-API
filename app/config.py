import os
from flask_emails import EmailsConfig

# uncomment the line below for postgres database url from environment variable
# postgres_local_base = os.environ['DATABASE_URL']

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', '2r3f0hp2boufb9p238ouisdabfl')
    DEBUG = False


class DevelopmentConfig(Config):
    # uncomment the line below to use postgres
    # SQLALCHEMY_DATABASE_URI = postgres_local_base
    DEBUG = True
    ENV = "dev"
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI') or 'sqlite:///' + os.path.join(basedir, 'dev.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'flask_boilerplate_test.db')
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # uncomment the line below to use postgres
    # SQLALCHEMY_DATABASE_URI = postgres_local_base


config_by_name = dict(
    dev=DevelopmentConfig,
    test=TestingConfig,
    prod=ProductionConfig
)

email_config = EmailsConfig(config={
    "EMAIL_HOST": str(os.environ["EMAIL_HOST"]),
    "EMAIL_PORT": str(os.environ["EMAIL_PORT"]),
    "EMAIL_HOST_USER": str(os.environ["EMAIL_HOST_USER"]),
    "EMAIL_HOST_PASSWORD": str(os.environ["EMAIL_HOST_PASSWORD"]),
    "EMAIL_USE_TLS": True
})

key = Config.SECRET_KEY