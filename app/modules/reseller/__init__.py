import random

from app import db
from app.models import UserRole
from app.modules.user.user_services import add_item as add_user_item

from .services.reseller_services import add_item
from .services.reseller_group_services import add_item as add_group_item


def import_test_data():
    from barnum import gen_data

    group_internal = add_group_item({
        "name": "Internal",
        "price_definition": {},
        "products": [1,2,3,4]
    })

    group_reps = add_group_item({
        "name": "Reps",
        "price_definition": {},
        "products": [1,2,3]
    })

    sales_role = db.session.query(UserRole).filter(UserRole.code == "sales").one()

    for index in range(10):
        email = gen_data.create_email()
        user = add_user_item({
            "username": email,
            "password": "test",
            "email": email,
            "roles": [sales_role.id]
        })
        add_item({
            "user_id": user.id,
            "group_id": group_internal.id if random.randint(0, 1) == 0 else group_reps.id,
            "email": email,
            "name": " ".join(gen_data.create_name()),
            "number": random.randint(10000,99999),
            "access_key": gen_data.create_pw(),
            "phone": gen_data.create_phone()
        })

