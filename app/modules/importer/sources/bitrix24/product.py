from app import db
import pprint
import json
import re
from datetime import datetime, timedelta

from app.models import Reseller, Product
from app.modules.product.product_services import add_item, update_item

from ._connector import post, get
from ._association import find_association, associate_item
from .customer import run_export as run_customer_export


def filter_import_data(item_data):
    product_group = ""
    pack_unit = ""
    catalog_data = post("crm.productsection.get", {"id": item_data["SECTION_ID"]})
    if catalog_data is not None and "result" in catalog_data:
        product_group = catalog_data["result"]["NAME"]
        while catalog_data["result"]["SECTION_ID"] is not None:
            catalog_data = post("crm.productsection.get", {"id": catalog_data["result"]["SECTION_ID"]})
            if catalog_data is not None and "result" in catalog_data:
                product_group = catalog_data["result"]["NAME"] + " - " + product_group
    unit_data = post("crm.measure.get", {"id": item_data["MEASURE"]})
    if unit_data is not None and "result" in unit_data:
        pack_unit = unit_data["result"]["MEASURE_TITLE"]
    item_data["NAME"] = item_data["NAME"].strip()
    packet_range_start = None
    packet_range_end = None
    if item_data["NAME"].find("PV Paket") == -1:
        if re.match(r"(.*) \([0-9\-]+\)$", item_data["NAME"]):
            if re.match(r"(.*) \([0-9]+\)$", item_data["NAME"]):
                search = re.search(r"(.*) \(([0-9]+)\)$", item_data["NAME"])
                packet_range_start = search.group(2)
                packet_range_end = search.group(2)
            else:
                search = re.search(r"(.*) \(([0-9]+)\-([0-9]+)\)$", item_data["NAME"])
                packet_range_start = search.group(2)
                packet_range_end = search.group(3)
                item_data["NAME"] = search.group(1)
    print(item_data["NAME"])
    data = {
        "product_group": product_group,
        "name": item_data["NAME"],
        "description": item_data["DESCRIPTION"],
        "weight": 0,
        "width": 0,
        "length": 0,
        "height": 0,
        "purchase_unit": 1,
        "reference_unit": 1,
        "pack_unit": pack_unit,
        "packet_range_start": packet_range_start,
        "packet_range_end": packet_range_end,
        "shipping_time": "",
        "tax_rate": 19,
        "min_purchase": 1,
        "price_net": item_data["PRICE"],
        "discount_percent": 0,
        "active": True
    }
    return data


def filter_export_data(lead):
    return None


def run_import(minutes=None):
    print("Loading Product List")
    products_data = {
        "next": 0
    }
    while "next" in products_data:
        products_data = post("crm.product.list", {
            "start": products_data["next"]
        })
        for product_raw_data in products_data["result"]:
            print("Remote ID: ", product_raw_data["ID"])
            local_link = find_association("Product", remote_id=product_raw_data["ID"])
            product_data = filter_import_data(product_raw_data)
            if product_data is not None:
                if local_link is None:
                    item = add_item(product_data)
                    if item is not None:
                        associate_item("Product", remote_id=product_raw_data["ID"], local_id=item.id)
                else:
                    item = db.session.query(Product).get(local_link.local_id)
                    if item is not None:
                        update_item(local_link.local_id, product_data)


def run_export(remote_id=None, local_id=None):
    pass
