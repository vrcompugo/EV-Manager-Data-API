import random
from datetime import timedelta, datetime as dt

from app import db
from app.models import Customer, Reseller

from .survey_services import add_item, update_item
from .models.survey import DATA_STATUSES, OFFER_STATUSES


def import_test_data():
    from barnum import gen_data

    customers = db.session.query(Customer).all()
    resellers = db.session.query(Reseller).all()
    data_statuses = [str(DATA_STATUSES.COMPLETE.value), str(DATA_STATUSES.INCOMPLETE.value)]
    offer_statuses = [str(OFFER_STATUSES.OPEN.value), str(OFFER_STATUSES.MISSING_DATA.value), str(OFFER_STATUSES.CREATED.value)]
    for index in range(30):
        customer = customers[random.randint(0,len(customers)-1)]
        reseller = resellers[random.randint(0,len(resellers)-1)]
        data_status = data_statuses[random.randint(0, len(data_statuses) - 1)]
        offer_status = offer_statuses[random.randint(0, len(offer_statuses) - 1)]
        datetime = dt.today() - timedelta(days=random.randint(0,200))
        survey = add_item({
            "customer_id": customer.id,
            "address_id": customer.default_address.id,
            "reseller_id": reseller.id,
            "datetime": datetime,
            "offer_until": datetime + timedelta(days=random.randint(6,10)),
            "data_status": data_status,
            "last_updated": datetime + timedelta(days=random.randint(6,10)),
            "data": {
              "ecar": "maybe-e-car",
              "pv_usage": "3300",
              "roof_datas": [
                {
                  "direction": "south",
                  "roof_type": "satteldach",
                  "roof_width": "0",
                  "roof_height": "7",
                  "roof_length": "0",
                  "roof_obstacles": [
                    {
                      "type": ""
                    }
                  ],
                  "roof_cover_type": "ziegel",
                  "roof_attack_angle": "38",
                  "roof_obstacles_comment": "teilweise verschattung durch gaube, deswegen Solar Edge, Angebote ohne Speicher von Mitbewerber teilw. mit Solar Edge ",
                  "roof_construction_method": "Aufdachsystem",
                  "roof_construction_distance": "to90cm"
                }
              ],
              "roof_files": [
                {
                  "id": "23",
                  "mime": "image/jpeg",
                  "label": "IMG_7928.JPG"
                },
                {
                  "id": "24",
                  "mime": "image/jpeg",
                  "label": "IMG_7931.JPG"
                }
              ],
              "heater_type": "warmepumpe",
              "project_name": "14016",
              "storage_size": "5.0",
              "location_type": "city",
              "electric_files": [
                {
                  "id": "25",
                  "mime": "image/jpeg",
                  "label": "IMG_7925.JPG"
                },
                {
                  "id": "26",
                  "mime": "image/jpeg",
                  "label": "IMG_7926.JPG"
                },
                {
                  "id": "27",
                  "mime": "image/jpeg",
                  "label": "IMG_7927.JPG"
                }
              ],
              "pv_max_kw_peak": "0",
              "pv_min_kw_peak": "4.95",
              "roof_obstacles": [],
              "pv_module_color": "Standard",
              "counter_location": "Keller",
              "counters_per_box": "2",
              "offer_all_in_one": True,
              "construction_beginn": "?",
              "current_net_company": "",
              "offer_cloud_special": True,
              "people_in_household": "4",
              "pv_requested_kw_peak": "6.44",
              "current_power_company": "",
              "current_counter_number": "",
              "power_company_kwh_cost": "",
              "power_company_base_cost": "",
              "heater_construction_year": "2007",
              "roof_construction_method": "Aufdachsystem",
              "power_company_customer_number": ""
            },
        })

        if data_status == "complete":
            update_item(survey.id, {
                "offer_status": offer_status
            })
