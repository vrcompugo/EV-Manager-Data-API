from app.modules.external.bitrix24.company import get_company
import json

from app import db
from app.modules.external.bitrix24.contact import get_contact, update_contact
from app.modules.settings import get_settings

from ._connector import post, put
from .company import export_by_bitrix_id as export_company_by_bitrix_id


def get_export_data(contact_data):
    data = {
        "contact": {
            "Name": f"{contact_data.get('first_name')} {contact_data.get('last_name')}",
            "ExternalId": f"C{contact_data.get('id')}",
            "IsPhysicalPerson": True,
            "Location": {
                "AddressString": f"{contact_data.get('street')} {contact_data.get('street_nb')}",
                "Postal": contact_data.get("zip"),
                "City": contact_data.get("city")
            },
            "MainContact": {
                "LastName": contact_data.get("last_name"),
                "FirstName": contact_data.get("first_name"),
                "Gender": "Female" if contact_data.get("salutation") == "ms" else "Male",
                "IsUser": False,
                "ExternalId": f"C{contact_data.get('id')}"
            }
        },
        "service_object": {
            "Name": f"{contact_data.get('street')} {contact_data.get('street_nb')}, {contact_data.get('zip')} {contact_data.get('city')}",
            "Location": {
                "AddressString": f"{contact_data.get('street')} {contact_data.get('street_nb')}",
                "Postal": contact_data.get("zip"),
                "City": contact_data.get("city")
            },
            "ExternalId": f"C{contact_data.get('id')}"
        }
    }
    if contact_data.get("email") is not None and len(contact_data.get("email")) > 0:
        data["contact"]["MainContact"]["Email"] = contact_data.get("email")[0]["VALUE"]
    if contact_data.get("phone") is not None and len(contact_data.get("phone")) > 0:
        data["contact"]["MainContact"]["Telephone"] = contact_data.get("phone")[0]["VALUE"]
    return data


def export_by_bitrix_id(bitrix_id):
    config = get_settings("external/mfr")
    print("export contact mfr")
    if config is None:
        print("no config")
        return None

    contact_data = get_contact(bitrix_id, force_reload=True)
    if contact_data.get("company_id") not in [None, "", 0]:
        company_data = get_company(contact_data.get("company_id"))
        if company_data is not None and company_data.get("street") not in ["", 0, False, None]:
            return export_company_by_bitrix_id(contact_data.get("company_id"))
    post_data = get_export_data(contact_data)
    if contact_data.get("mfr_id", None) in ["", None, 0]:
        response = post("/Companies", post_data=post_data["contact"])
        if response.get("Id") not in ["", None, 0]:
            mfr_id = response.get("Id")
            post_data["service_object"]["CompanyId"] = response.get("Id")
            response = post("/ServiceObjects", post_data=post_data["service_object"])
            if response.get("Id") in ["", None, 0]:
                print(json.dumps(response, indent=2))
            else:
                update_contact(bitrix_id, {"mfr_id": mfr_id, "mfr_service_object_id": response.get("Id")})
    else:
        post_data["Id"] = int(contact_data.get('mfr_id'))
        response = put(f"/Companies({contact_data.get('mfr_id')}L)", post_data=post_data)
        # TODO does not work yet. Response error: System.NullReferenceException: Object reference not set to an instance of an object
