import os
import unittest
from flask_migrate import Migrate, MigrateCommand, upgrade
from flask_script import Manager, prompt_bool
import sqlalchemy as sa

from app import create_app, db
from app.blueprint import blueprint
from app.modules.bitrix24.bitrix24_routes import bitrix24_bp

app = create_app(os.getenv('ENVIRONMENT') or 'dev')
app.register_blueprint(blueprint)
app.register_blueprint(bitrix24_bp, url_prefix="/bitrix24")


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
def update_commission_values():
    from commands.update_commission_values import update_commission_values
    update_commission_values()


@manager.command
def lead_comment_test():
    from commands.lead_comment_test import lead_comment_test
    lead_comment_test()


@manager.command
def cron_import_tasks():
    from commands.cron_import_tasks import cron_import_tasks
    cron_import_tasks()


@manager.command
def update_role_permissions():
    from app.modules.user import update_role_permissions
    update_role_permissions()


@manager.option("-l", "--local_id", dest='local_id', default=None)
def auto_assign_lead(local_id):
    from app.modules.lead.lead_services import Lead, lead_reseller_auto_assignment
    if local_id is not None:
        lead = db.session.query(Lead).get(local_id)
        if lead is not None:
            lead_reseller_auto_assignment(lead)


@manager.command
def cron():
    from app.modules.importer import cron
    cron()


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
