from app import db


def import_test_data():
    from .product_services import add_item, update_item
    print("Product import")
    add_item({
        "number": "power",
        "name": "Efi-Strom"
    })
    add_item({
        "number": "gas",
        "name": "Efi-Gas"
    })
    add_item({
        "number": "ccloud",
        "name": "cCloud"
    })
    add_item({
        "number": "ccloud2",
        "name": "cCloud Pro"
    })
    add_item({
        "number": "ccloud-special",
        "name": "cCloud Special"
    })
    add_item({
        "number": "ccloud-zero",
        "name": "cCloud Zero"
    })

