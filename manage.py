import os
import unittest

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager

from app import create_app, db
import sqlalchemy as sa

app = create_app(os.getenv('ENVIRONMENT') or 'dev')
from app.blueprint import blueprint
app.register_blueprint(blueprint)


app.app_context().push()

manager = Manager(app)

migrate = Migrate(app, db)

manager.add_command('db', MigrateCommand)

@manager.command
def run():
    app.run(host="0.0.0.0")


@manager.command
def install():
    from app.models import User, UserRole
    import datetime
    admin_role = UserRole(label="root", code="root",permissions=["all"])
    user = User(
        email="a.hedderich@hbundb.de",
        username="root",
        password="Mw05mTGkew7bYTH7W5UF7G5mBpisCF2M",
        role=admin_role,
        registered_on=datetime.datetime.now()
    )
    db.session.add(user)
    db.session.commit()

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
