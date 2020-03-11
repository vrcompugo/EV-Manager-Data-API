import json
import datetime

from app.models import User, Reseller, Customer, Order
from app.modules.calendar.calendar_services import add_item, update_item

from ._connector import post, get
from ._association import find_association, associate_item


def convert_datetime(raw):
    if raw is None:
        return None
    if raw.find(":") > 0:
        return datetime.datetime.strptime(raw, "%d.%m.%Y %H:%M:%S")
    return datetime.datetime.strptime(raw, "%d.%m.%Y")


def filter_import_data(item_data):
    user_link = find_association("User", remote_id=item_data["OWNER_ID"])
    if user_link is None:
        return None
    user = User.query.filter(User.id == user_link.local_id).first()
    if user is None:
        return None

    data = {
        "customer_id": None,
        "user_id": user.id,
        "reseller_id": None,
        "order_id": None,
        "distance_km": 0,
        "travel_time_minutes": 0,
        "lat": 0.0,
        "lng": 0.0,
        "type": "",
        "begin": convert_datetime(item_data["DATE_FROM"]),
        "end": convert_datetime(item_data["DATE_TO"]),
        "comment": item_data["NAME"],
        "status": None
    }
    if data["begin"] == data["end"]:
        data["end"] = datetime.datetime(data["end"].year, data["end"].month, data["end"].day, 23, 59, 59)

    reseller = Reseller.query.filter(Reseller.user_id == user.id).first()
    if reseller is not None:
        data["reseller_id"] = reseller.id

    if "UF_CRM_CAL_EVENT" in item_data and item_data["UF_CRM_CAL_EVENT"] is not False:
        for crm_link in item_data["UF_CRM_CAL_EVENT"]:
            (link_type, link_id) = crm_link.split("_")
            if link_type == "D":
                order_link = find_association("Order", remote_id=int(link_id))
                if order_link is not None:
                    data["order_id"] = order_link.local_id
            if link_type == "C":
                customer_link = find_association("Customer", remote_id=int(link_id))
                if customer_link is not None:
                    customer = Customer.query.filter(Customer.id == customer_link.local_id).first()
                    if customer is not None:
                        data["customer_id"] = customer.id
                        data["salutation"] = customer.salutation
                        data["title"] = customer.title
                        data["firstname"] = customer.firstname
                        data["lastname"] = customer.lastname
                        data["company"] = customer.company
                        data["street"] = customer.default_address.street
                        data["street_nb"] = customer.default_address.street_nb
                        data["street_extra"] = customer.default_address.street_extra
                        data["zip"] = customer.default_address.zip
                        data["city"] = customer.default_address.city
    return data


def run_import():
    users = User.query.filter(User.active.is_(True)).all()
    for user in users:
        link = find_association("User", local_id=user.id)
        if link is not None:
            response = post("calendar.event.get", post_data={
                "type": "user",
                "ownerId": link.remote_id,
                "from": '2020-03-03',
                "to": '2021-03-03',
            })
            if "result" in response:
                for item_data in response["result"]:
                    data = filter_import_data(item_data)
                    event_link = find_association("CalendarEvent", remote_id=item_data["ID"] + str(link.remote_id))
                    if event_link is None:
                        event = add_item(data)
                    else:
                        event = update_item(event_link.local_id, data)
                    if event_link is None and event is not None:
                        associate_item("CalendarEvent", remote_id=item_data["ID"] + str(link.remote_id), local_id=event.id)
                    print("calendar event:", item_data["ID"] + str(link.remote_id), event, data["begin"], data["end"])
    return None
