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
    sales_role = UserRole(label=u"Verkäufer", code="sales", permissions=full_permission_list)
    sales_lead_role = UserRole(label="Verkaufsleiter", code="sales_lead", permissions=full_permission_list)
    front_office_role = UserRole(label="Front Office", code="front_office", permissions=full_permission_list)
    bookkeeping_role = UserRole(label="Buchhaltung", code="bookkeeping", permissions=full_permission_list)
    cloud_manager_role = UserRole(label="Cloud Manager", code="cloud_manager", permissions=full_permission_list)
    evu_manager_role = UserRole(label="EVU Manager", code="evu_manager", permissions=full_permission_list)
    construction_lead_role = UserRole(label="Montageleiter", code="construction_lead", permissions=full_permission_list)
    construction_role = UserRole(label="Monteur", code="construction", permissions=full_permission_list)
    warehouse_role = UserRole(label="Lagerverwaltung", code="warehouse", permissions=full_permission_list)
    customer_service_role = UserRole(label="Kunden Service", code="customer_service", permissions=full_permission_list)
    insurance_role = UserRole(label="Versicherung", code="insurance", permissions=full_permission_list)
    maintenance_role = UserRole(label="Wartung", code="maintenance", permissions=full_permission_list)
    wl_partner_role = UserRole(label="White-Label-Partner", code="white-label-partner", permissions=["cloud_calculation"])

    db.session.add_all(
        [admin_role, dev_role, sales_role, sales_lead_role, front_office_role, bookkeeping_role, cloud_manager_role,
         evu_manager_role, construction_lead_role, construction_role, warehouse_role, customer_service_role,
         insurance_role, maintenance_role, wl_partner_role])
    db.session.commit()

    role_ids = []
    roles = db.session.query(UserRole).all()
    for role in roles:
        role_ids.append(role.id)
    add_item({
        "username": "root",
        "password": password,
        "email": "root@hbundb.de",
        "roles": role_ids
    })


def update_role_permissions():
    from app.blueprint import full_permission_list
    admin_role = db.session.query(UserRole).filter(UserRole.code == "root").first()
    admin_role.permissions = full_permission_list + ["create_root_user"]
    for role in ["dev", "sales", "sales_lead", "front_office", "bookkeeping", "cloud_manager",
                 "evu_manager", "construction_lead", "construction", "warehouse", "customer_service",
                 "insurance", "maintenance"]:
        role_object = db.session.query(UserRole).filter(UserRole.code == role).first()
        role_object.permissions = full_permission_list
    db.session.commit()


def import_test_data():
    role_ids = []
    roles = db.session.query(UserRole).all()
    for role in roles:
        role_ids.append(role.id)
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
        "roles": role_ids
    })
