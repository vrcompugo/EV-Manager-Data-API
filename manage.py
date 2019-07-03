import os
import unittest
from flask_migrate import Migrate, MigrateCommand, upgrade
from flask_script import Manager, prompt_bool
import sqlalchemy as sa

from app import create_app, db
from app.blueprint import blueprint

app = create_app(os.getenv('ENVIRONMENT') or 'dev')
app.register_blueprint(blueprint)


app.app_context().push()

manager = Manager(app)

migrate = Migrate(app, db)

manager.add_command('db', MigrateCommand)

@manager.command
def run():
    upgrade()
    app.run(host="0.0.0.0")


@manager.command
def install():
    upgrade()
    from app.modules.user import install as user_install
    user_install()


@manager.option("-m", "--module", dest='module', default=None)
def deploy_test_data(module):
    if prompt_bool(
            "Are you sure you want to import test data"):
        if module is None or module == "user":
            from app.modules.user import import_test_data as user_test_data
            user_test_data()
        if module is None or module == "customer":
            from app.modules.customer import import_test_data as customer_test_data
            customer_test_data()
        if module is None or module == "reseller":
            from app.modules.reseller import import_test_data as reseller_test_data
            reseller_test_data()
        if module is None or module == "survey":
            from app.modules.survey import import_test_data as survey_test_data
            survey_test_data()


@manager.command
def test():
    """Runs the unit tests."""
    tests = unittest.TestLoader().discover('test', pattern='test*.py')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if result.wasSuccessful():
        return 0
    return 1


if __name__ == '__main__':
    sa.orm.configure_mappers()
    manager.run()
