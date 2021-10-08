import os
import json
from time import sleep
import unittest
from flask_migrate import Migrate, MigrateCommand, upgrade
from flask_script import Manager, prompt_bool
import sqlalchemy as sa

from app import create_app, db
from app.blueprint import register_blueprints

app = create_app(os.getenv('ENVIRONMENT') or 'dev')
register_blueprints(app)

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


@manager.command
def update_role_permissions():
    from app.modules.user import update_role_permissions
    update_role_permissions()


@manager.command
def sign_date_test():
    import datetime
    from app.modules.external.bitrix24.lead import update_lead, get_lead
    print("sign_date_test")
    lead_data = {}
    lead_data["order_sign_date"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S-01:00")
    # lead_data["order_sign_date"] = str(datetime.datetime.now())
    print(lead_data)
    update_lead("30162", lead_data)


@manager.command
def import_mfr_tasks():
    from app.modules.external.bitrix24.task import get_tasks
    print("import mfr tasks")
    tasks = get_tasks({
        "select": "full",
        "filter[>ACTIVITY_DATE]": "2021-07-26",
        "filter[TITLE]": "%[mfr]%"
    })
    print(len(tasks))


@manager.command
def test_special():
    from app.models import OfferV2, Order, ImportIdAssociation
    from app.modules.importer.sources.bitrix24.order import run_export as run_order_export
    offers = OfferV2.query.filter(OfferV2.is_sent.is_(True)).all()
    for offer in offers:
        orders = Order.query.filter(Order.offer_id == offer.id).all()
        for order in orders:
            link = ImportIdAssociation.query\
                .filter(ImportIdAssociation.local_id == order.id)\
                .filter(ImportIdAssociation.source == 'bitrix24')\
                .filter(ImportIdAssociation.model == 'Order')\
                .first()
            if link is None:
                print("order", order.id)
                run_order_export(local_id=order.id)



@manager.command
def run_legacy_folder_creation():
    from app.modules.external.bitrix24.drive import run_legacy_folder_creation
    run_legacy_folder_creation()


@manager.command
def run_mfr_subscriptor():
    from app.modules.external.mfr.amqp import run_mfr_amqp_messaging_subscriptor
    run_mfr_amqp_messaging_subscriptor()


@manager.option("-s", "--section", dest='section', default=None)
def cron(section):
    from app.modules.cron import cron
    cron(section)


@manager.option("-m", "--module", dest='module', default=None)
@manager.option("-s", "--source", dest='source', default=None)
@manager.option("-l", "--local_id", dest='local_id', default=None)
@manager.option("-r", "--remote_id", dest='remote_id', default=None)
@manager.option("-y", "--y", dest='yes', default=None)
def import_remote_data(yes, source, module, local_id, remote_id):
    if source is None:
        print("No source parameter given -s or --source")
        return
    if yes is not None or prompt_bool(
            "Are you sure you want to import from remote source: {}".format(source)):
        from app.modules.importer.import_services import import_by_source_module
        import_by_source_module(source=source, model=module, local_id=local_id, remote_id=remote_id)


@manager.option("-m", "--module", dest='module', default=None)
@manager.option("-s", "--source", dest='source', default=None)
@manager.option("-l", "--local_id", dest='local_id', default=None)
@manager.option("-r", "--remote_id", dest='remote_id', default=None)
@manager.option("-y", "--y", dest='yes', default=None)
def export_remote_data(yes, source, module, local_id, remote_id):
    if source is None:
        print("No source parameter given -s or --source")
        return
    if yes is not None or prompt_bool(
            "Are you sure you want to import from remote source: {}".format(source)):
        from app.modules.importer.export_services import export_by_source_module
        export_by_source_module(source=source, model=module, local_id=local_id, remote_id=remote_id)


@manager.command
@manager.option("-t", "--test", dest='test_name', default=None)
def test(test_name=None):
    """Runs the unit tests."""
    if test_name is not None:
        tests = unittest.TestLoader().discover('test', pattern=f'test_{test_name}.py')
    else:
        tests = unittest.TestLoader().discover('test', pattern='test*.py')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if result.wasSuccessful():
        return 0
    return 1


if __name__ == '__main__':
    sa.orm.configure_mappers()
    manager.run()
