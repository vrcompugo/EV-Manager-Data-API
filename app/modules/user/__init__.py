from flask_script import prompt

from app import db

from .models import UserRole
from .user_services import add_item


def install():
    from app.blueprint import full_permission_list

    password = prompt("root password")
    if password is None:
        print("Installation canceled")
        return

    admin_role = UserRole(label="root", code="root", permissions=full_permission_list + ["create_root_user"])
    dev_role = UserRole(label="Entwickler", code="dev", permissions=full_permission_list)
    sales_role = UserRole(label=u"Verkäufer", code="sales", permissions=[])
    sales_lead_role = UserRole(label="Verkaufsleiter", code="sales_lead", permissions=[])
    front_office_role = UserRole(label="Front Office", code="front_office", permissions=[])
    bookkeeping_role = UserRole(label="Buchhaltung", code="bookkeeping", permissions=[])
    cloud_manager_role = UserRole(label="Cloud Manager", code="cloud_manager", permissions=[])
    evu_manager_role = UserRole(label="EVU Manager", code="evu_manager", permissions=[])
    construction_lead_role = UserRole(label="Montageleiter", code="construction_lead", permissions=[])
    construction_role = UserRole(label="Monteur", code="construction", permissions=[])
    warehouse_role = UserRole(label="Lagerverwaltung", code="warehouse", permissions=[])
    customer_service_role = UserRole(label="Kunden Service", code="customer_service", permissions=[])
    insurance_role = UserRole(label="Versicherung", code="insurance", permissions=[])
    maintenance_role = UserRole(label="Wartung", code="maintenance", permissions=[])

    db.session.add_all(
        [admin_role, dev_role, sales_role, sales_lead_role, front_office_role, bookkeeping_role, cloud_manager_role,
         evu_manager_role, construction_lead_role, construction_role, warehouse_role, customer_service_role,
         insurance_role, maintenance_role])
    db.session.flush()

    add_item({
        "username": "root",
        "password": password,
        "email": "a.hedderich@hbundb.de",
        "roles": [admin_role.id]
    })


def import_test_data():
    dev_role = db.session.query(UserRole).filter(UserRole.code == "dev").one()
    username = prompt("dev username")
    if username is None:
        print("import canceled")
        return
    password = prompt("dev password")
    if password is None:
        print("import canceled")
        return
    email = prompt("dev email")
    if email is None:
        print("import canceled")
        return
    add_item({
        "username": username,
        "password": password,
        "email": email,
        "roles": [dev_role.id]
    })

