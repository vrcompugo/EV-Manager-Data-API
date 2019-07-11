import random


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

    for index in range(10):
        email = gen_data.create_email()
        add_item({
            "group_id": group_internal.id if random.randint(0, 1) == 0 else group_reps.id,
            "email": email,
            "name": " ".join(gen_data.create_name()),
            "number": random.randint(10000,99999),
            "access_key": gen_data.create_pw(),
            "phone": gen_data.create_phone()
        })

