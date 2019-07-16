from app import db


def import_test_data():
    from .product_services import add_item, update_item
    print("Product import")
    add_item({
        "number": "power",
        "type": "tarif",
        "name": "Efi-Strom"
    })
    add_item({
        "number": "gas",
        "type": "tarif",
        "name": "Efi-Gas"
    })
    add_item({
        "number": "ccloud",
        "type": "tarif",
        "name": "cCloud"
    })
    add_item({
        "number": "ccloud2",
        "type": "tarif",
        "name": "cCloud Pro"
    })
    add_item({
        "number": "ccloud-special",
        "type": "tarif",
        "name": "cCloud Special"
    })
    add_item({
        "number": "ccloud-zero",
        "type": "tarif",
        "name": "cCloud Zero"
    })
    add_item({
        "number": "pv-system",
        "type": "product",
        "name": "PV-Anlage"
    })

