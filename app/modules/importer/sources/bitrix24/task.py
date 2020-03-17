import json
import pprint
import datetime

from app.models import User, Reseller, Customer, Order
from app.modules.task.task_services import add_item, update_item
from app.utils.error_handler import error_handler
from app.modules.settings.settings_services import get_one_item as get_config_item, update_item as update_config_item

from ._connector import post, get
from ._association import find_association, associate_item
from .order import run_import as order_import


def convert_datetime(raw):
    if raw is None or raw == "":
        return None
    raw = raw.replace("T", " ")
    if raw.find("+") > 0:
        raw = raw[:raw.find("+")]
    if raw.find(":") > 0:
        return datetime.datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    return datetime.datetime.strptime(raw, "%Y-%m-%d")


def customer_data(id, data):
    customer = Customer.query.filter(Customer.id == id).first()
    if customer is not None:
        data["customer_id"] = customer.id
        data["salutation"] = customer.salutation
        data["title"] = customer.title
        data["firstname"] = customer.firstname
        data["lastname"] = customer.lastname
        data["company"] = customer.company
        if "street" not in data:
            data["street"] = customer.default_address.street
            data["street_nb"] = customer.default_address.street_nb
        if "zip" not in data:
            data["zip"] = customer.default_address.zip
            data["city"] = customer.default_address.city
    return data


def filter_import_data(item_data):
    if "responsibleId" not in item_data:
        print("no user")
        return None
    user_link = find_association("User", remote_id=item_data["responsibleId"])
    if user_link is None:
        print("no user")
        return None
    user = User.query.filter(User.id == user_link.local_id).first()
    if user is None:
        print("no user")
        return None

    members = [user]
    if "accomplices" in item_data:
        for member_id in item_data["accomplices"]:
            member_link = find_association("User", remote_id=member_id)
            if member_link is not None:
                member = User.query.filter(User.id == member_link.local_id).first()
                if member is not None:
                    members.append(member)
    data = {
        "remote_id": item_data["id"],
        "user_id": user.id,
        "reseller_id": None,
        "customer_id": None,
        "lead_id": None,
        "order_id": None,
        "members": members,
        "type": "",
        "begin": convert_datetime(item_data["startDatePlan"]),
        "end": convert_datetime(item_data["endDatePlan"]),
        "deadline": convert_datetime(item_data["deadline"]),
        "label": item_data["title"],
        "comment": item_data["description"],
        "status": None
    }
    if data["begin"] == data["end"] and data["end"] is not None:
        data["end"] = datetime.datetime(data["end"].year, data["end"].month, data["end"].day, 23, 59, 59)
    if data["begin"] is not None and data["end"] is None:
        data["end"] = data["begin"] + datetime.timedelta(minutes=15)

    reseller = Reseller.query.filter(Reseller.user_id == user.id).first()
    if reseller is not None:
        data["reseller_id"] = reseller.id

    if "ufCrmTask" in item_data and item_data["ufCrmTask"] is not False:
        for crm_link in item_data["ufCrmTask"]:
            (link_type, link_id) = crm_link.split("_")
            if link_type == "D":
                order_link = find_association("Order", remote_id=int(link_id))
                if order_link is None:
                    order_import(remote_id=int(link_id))
                    order_link = find_association("Order", remote_id=int(link_id))
                if order_link is not None:
                    data["order_id"] = order_link.local_id
                    order = Order.query.filter(Order.id == order_link.local_id).first()
                    if order is not None:
                        data["type"] = order.type
                        data = customer_data(order.customer_id, data)
                        data["street"] = order.street
                        data["street_nb"] = order.street_nb
                        data["zip"] = order.zip
                        data["city"] = order.city
            if link_type == "L":
                lead_link = find_association("Lead", remote_id=int(link_id))
                if lead_link is not None:
                    data["lead_id"] = lead_link.local_id
            if link_type == "C":
                customer_link = find_association("Customer", remote_id=int(link_id))
                if customer_link is not None:
                    data = customer_data(customer_link.local_id, data)
    return data


def run_import(local_id=None, remote_id=None):
    if local_id is not None:
        link = find_association("Task", local_id=local_id)
        if link is not None:
            remote_id = link.remote_id
    if remote_id is None:
        print("no id given")
        return None
    response = post("tasks.task.get", {
        "taskId": remote_id
    })
    if "result" in response and "task" in response["result"]:
        item_data = response["result"]["task"]
        data = filter_import_data(item_data)
        if data is not None:
            task_link = find_association("Task", remote_id=item_data["id"])
            if task_link is None:
                task = add_item(data)
            else:
                task = update_item(task_link.local_id, data)
            if task is not None:
                print("task imported:", task.id)
            if task_link is None and task is not None:
                associate_item("Task", remote_id=item_data["id"], local_id=task.id)
        else:
            print("task", item_data["id"], item_data)
    return None


def run_cron_import():
    config = get_config_item("importer/bitrix24")
    post_data = {
        "ORDER[CHANGED_DATE]": "ASC"
    }
    if config is not None and "data" in config and "last_task_import" in config["data"]:
        post_data["filter[>CHANGED_DATE]"] = config["data"]["last_task_import"]

    response = {"next": 0}
    while "next" in response:
        post_data["start"] = response["next"]
        response = post("tasks.task.list", post_data=post_data)
        if "result" in response and "tasks" in response["result"]:
            for item_data in response["result"]["tasks"]:
                try:
                    run_import(remote_id=item_data["id"])
                except Exception as e:
                    error_handler()

    config = get_config_item("importer/bitrix24")
    if config is not None and "data" in config:
        config["data"]["last_task_import"] = str(datetime.datetime.now())
    update_config_item("importer/bitrix24", config)
