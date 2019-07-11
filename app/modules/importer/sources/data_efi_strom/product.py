from app import db
from app.models import Product
from app.modules.product.product_services import add_item

from ._connector import post
from ._association import find_association, associate_item


def filter_input(data):

    data["number"] = data["key"]

    return data


def run_import():
    data = post("Form")
    if "items" in data:
        for item_data in data["items"]:

            item_data = filter_input(item_data)

            item = find_association(model="Product", remote_id=item_data["id"])
            if item is None:
                product = db.session.query(Product).filter(Product.number == item_data["number"]).first()
                if product is None:
                    item = add_item(item_data)
                    if item is not None:
                        associate_item(model="Product", remote_id=item_data["id"], local_id=item.id)
                else:
                    associate_item(model="Product", remote_id=item_data["id"], local_id=product.id)
        return True
    return False
