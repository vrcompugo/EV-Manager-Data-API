import re
import os
import json
import datetime

from app import db
from app.exceptions import ApiException
from app.models import Bitrix24ProductCache
from app.modules.external.bitrix24._field_values import convert_field_euro_from_remote
from app.modules.settings import get_settings
from app.modules.external.bitrix24.drive import get_file_content, get_file_content_cached, get_file

from ._connector import get, post


def reload_products(filters=None, force=False):
    cache = Bitrix24ProductCache.query.order_by(Bitrix24ProductCache.datetime.asc()).first()
    if not force and cache is not None and cache.datetime > datetime.datetime.now() - datetime.timedelta(minutes=3600):
        return None
    import_datetime = datetime.datetime.now()
    config = get_settings(section="external/bitrix24")
    categories = config["product"]["categories"]
    units = config["product"]["units"]
    payload = {}
    if filters is not None:
        for filter_key in filters.keys():
            payload[filter_key.upper()] = filters[filter_key]
    payload["start"] = 0
    result = []
    while payload["start"] is not None:
        print("product_import", payload["start"])
        data = post("crm.product.list", payload)
        if "result" in data:
            payload["start"] = data["next"] if "next" in data else None
            for item in data["result"]:
                if item["NAME"] == "Abfallentsorgung":
                    print(str(item["SECTION_ID"]))
                if str(item["SECTION_ID"]) == str(categories["PV Module"]):
                    kwp = re.search(r"(.*) ([0-9]+) Watt(.*)\(([0-9,]+)qm\)$", item["NAME"])
                    if kwp is not None and kwp.group(2) != "":
                        item["kwp"] = int(kwp.group(2)) / 1000
                    if kwp is not None and kwp.group(4) != "":
                        try:
                            item["qm"] = float(kwp.group(4).replace(",", "."))
                            item["NAME"] = item["NAME"].replace(f" ({item['qm']}qm)")
                        except Exception as e:
                            pass
                item["quantity_unit"] = units[str(item["MEASURE"])]
                if re.match(r"(.*) \[[0-9\-]+\]\[(.*)\]$", item["NAME"]):
                    search = re.search(r"(.*) \[([0-9\-]+)\]\[(.*)\]$", item["NAME"])
                    dash_index = search.group(2).find("-")
                    if dash_index >= 0:
                        item["range_start"] = float(search.group(2)[:dash_index])
                        item["range_end"] = float(search.group(2)[dash_index + 1:])
                    else:
                        item["range_start"] = float(search.group(2))
                        item["range_end"] = item["range_start"]
                    item["range_type"] = search.group(3)
                    item["NAME"] = search.group(1)
                item["NAME"] = item["NAME"].strip()
            result = result + data["result"]
        else:
            print("error1:", data)
            payload["start"] = None
            return None
    for product in result:
        item = Bitrix24ProductCache.query.filter(Bitrix24ProductCache.product_id == product.get("ID")).first()
        if item is None:
            item = Bitrix24ProductCache(product_id=product.get("ID"))
            db.session.add(item)
        item.name = product.get("NAME")
        item.catalog_id = product.get("CATALOG_ID")
        item.section_id = product.get("SECTION_ID")
        item.datetime = import_datetime
        item.data = product
    deleteds = Bitrix24ProductCache.query.filter(Bitrix24ProductCache.datetime < import_datetime - datetime.timedelta(minutes=5)).all()
    for deleted in deleteds:
        db.session.delete(deleted)
    db.session.commit()
    return result


def load_cache():
    items = Bitrix24ProductCache.query.order_by(Bitrix24ProductCache.datetime.asc()).all()
    if len(items) == 0:
        return None
    product_cache = {
        "last_import": items[0].datetime,
        "products": []
    }
    for item in items:
        product_cache["products"].append(item.data)
    return product_cache


def get_list(filters=None):
    product_cache = load_cache()
    if product_cache is None:
        reload_products(filters)
        product_cache = load_cache()
    if "products" not in product_cache or product_cache["products"] is None:
        reload_products(filters)
        product_cache = load_cache()
    if "last_import" not in product_cache or product_cache["last_import"] is None:
        reload_products(filters)
        product_cache = load_cache()
    if product_cache["last_import"] < datetime.datetime.now() - datetime.timedelta(days=1):
        reload_products(filters)
        product_cache = load_cache()
    return product_cache["products"]


def get_product(label, category, data=None):
    config = get_settings(section="external/bitrix24")
    categories = config["product"]["categories"]
    products = get_list()
    for product in products:
        if category not in categories:
            continue
        if product["NAME"] == label and str(product["SECTION_ID"]) == str(categories[category]):
            if data is not None and product.get("range_type", None) is not None:
                if product.get("range_type") == "heating_sqm":
                    print(product.get("range_start"), float(data["heating_quote_sqm"]), product.get("range_end"))
                    if product.get("range_start") < float(data["heating_quote_sqm"]) <= product.get("range_end"):
                        return json.loads(json.dumps(product))
                if product.get("range_type") == "dqm":
                    if product.get("range_start") < float(data["roof_sqm"]) <= product.get("range_end"):
                        return json.loads(json.dumps(product))
                if product.get("range_type") == "personen":
                    if product.get("range_start") < float(data) <= product.get("range_end"):
                        return json.loads(json.dumps(product))
            else:
                return json.loads(json.dumps(product))
    raise Exception(f"product '{label}' '{category}' not found")
