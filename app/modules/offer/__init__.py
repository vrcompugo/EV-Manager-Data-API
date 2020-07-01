import random
from datetime import timedelta, datetime as dt

from app import db


def import_test_data():
    from app.models import Survey
    from barnum import gen_data
    from .offer_services import add_item, update_item

    statuses = [
        "created", "sent_out", "declined", "accepted"
    ]

    surveys = db.session.query(Survey).filter(Survey.offer_status == "open").all()
    for survey in surveys:
        add_item({
            "product_id": random.randint(5,6),
            "customer_id": survey.customer_id,
            "address_id": survey.address_id,
            "payment_account_id": survey.customer.default_payment_account_id,
            "reseller_id": survey.reseller_id,
            "datetime": survey.datetime + timedelta(days=random.randint(1,8)),
            "status": statuses[random.randint(0,3)],
            "data": {
              "cloud_special": {
                "files": [
                  {
                    "id": "74",
                    "mime": "image/jpeg",
                    "label": "IMG_6456.JPG"
                  },
                  {
                    "id": "75",
                    "mime": "image/jpeg",
                    "label": "IMG_6457.JPG"
                  },
                  {
                    "id": "76",
                    "mime": "image/jpeg",
                    "label": "IMG_6458.JPG"
                  },
                  {
                    "id": "77",
                    "mime": "image/jpeg",
                    "label": "IMG_6459.JPG"
                  },
                  {
                    "id": "78",
                    "mime": "image/jpeg",
                    "label": "IMG_6460.JPG"
                  },
                  {
                    "id": "79",
                    "mime": "image/jpeg",
                    "label": "IMG_6461.JPG"
                  },
                  {
                    "id": "80",
                    "mime": "image/jpeg",
                    "label": "IMG_6462.JPG"
                  },
                  {
                    "id": "81",
                    "mime": "image/jpeg",
                    "label": "IMG_6463.JPG"
                  },
                  {
                    "id": "82",
                    "mime": "image/jpeg",
                    "label": "IMG_6464.JPG"
                  }
                ],
                "drains": [
                  {
                    "city": survey.customer.default_address.zip + " " + survey.customer.default_address.city,
                    "type": "privat",
                    "usage": "100",
                    "street": survey.customer.default_address.street + " " + survey.customer.default_address.street_nb,
                    "comment": "",
                    "company": None,
                    "lastname": survey.customer.lastname,
                    "firstname": survey.customer.firstname,
                    "efficiancy": 40,
                    "counter_number": "1PAFDA72077763"
                  }
                ],
                "pvgains": [
                  {
                    "city": survey.customer.default_address.zip + " " + survey.customer.default_address.city,
                    "pvkw": "9.9",
                    "usage": "7500",
                    "pvtype": "roof",
                    "street": survey.customer.default_address.street + " " + survey.customer.default_address.street_nb,
                    "comment": "Zählerkonzept 8",
                    "company": None,
                    "is_drain": True,
                    "lastname": survey.customer.lastname,
                    "direction": "west_east",
                    "firstname": survey.customer.firstname,
                    "efficiancy": "880",
                    "counter_number": "1PAFDA72054536",
                    "drainefficiancy": "60"
                  }
                ],
                "invlation": "1.75",
                "customer_type": "privat",
                "price_increase": "4.25",
                "investment_cost": "",
                "current_energie_cost": ""
              }
            },
            "price_definition": {
                "ap3": 23.98,
                "rates": [
                    {
                        "type": "roof",
                        "upto": 10,
                        "feedrate": 11.11
                    },
                    {
                        "type": "roof",
                        "upto": 40,
                        "feedrate": 10.81
                    },
                    {
                        "type": "roof",
                        "upto": 100,
                        "feedrate": 8.5
                    },
                    {
                        "type": "roof",
                        "upto": 1000,
                        "feedrate": 8.05
                    },
                    {
                        "type": "freerange",
                        "feedrate": 7.68
                    }
                ],
                "taxrate": 16,
                "base_per_drain": 12.5
            },
            "errors": []
        })
