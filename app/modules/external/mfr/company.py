import json

from app import db
from app.modules.external.bitrix24.company import get_company, update_company, get_company_contacts
from app.modules.external.bitrix24.contact import get_contact, update_contact
from app.modules.settings import get_settings

from ._connector import post, put


def get_export_data(company_data, contact_data):
    data = {
        "company": {
            "Name": company_data.get("title"),
            "IsPhysicalPerson": False,
            "Location": {
                "AddressString": f"{company_data.get('street')} {company_data.get('street_nb')}",
                "Postal": str(company_data.get("zip")),
                "City": str(company_data.get("city"))
            },
            "ExternalId": f"Cp{company_data.get('id')}"
        },
        "contact": None,
        "service_object": {
            "Name": f"{company_data.get('street')} {company_data.get('street_nb')}, {company_data.get('zip')} {company_data.get('city')}",
            "Location": {
                "AddressString": f"{company_data.get('street')} {company_data.get('street_nb')}",
                "Postal": str(company_data.get("zip")),
                "City": str(company_data.get("city"))
            },
            "ExternalId": f"Cp{company_data.get('id')}"
        }
    }
    if contact_data is not None:
        data["contact"] = {
            "LastName": contact_data.get("last_name"),
            "FirstName": contact_data.get("first_name"),
            "Gender": "Female" if contact_data.get("salutation") == "ms" else "Male",
            "IsUser": False,
            "ExternalId": f"C{contact_data.get('id')}"
        }
        if contact_data.get("email") is not None and len(contact_data.get("email")) > 0:
            data["contact"]["Email"] = contact_data.get("email")[0]["VALUE"]
        if contact_data.get("phone") is not None and len(contact_data.get("phone")) > 0:
            data["contact"]["Telephone"] = contact_data.get("phone")[0]["VALUE"]
    return data


def export_by_bitrix_id(bitrix_id):
    config = get_settings("external/mfr")
    print("export company mfr")
    if config is None:
        print("no config")
        return None

    company_data = get_company(bitrix_id)
    contacts = get_company_contacts(bitrix_id)
    contact_data = None
    if isinstance(contacts, list) and len(contacts[0]):
        contact_data = get_contact(contacts[0].get("CONTACT_ID"))
    post_data = get_export_data(company_data, contact_data)
    if company_data.get("mfr_id", None) in ["", None, 0]:
        response = post("/Companies", post_data=post_data["company"])
        if response.get("Id") not in ["", None, 0]:
            mfr_id = response.get("Id")
            if post_data["contact"] is not None:
                post_data["contact"]["CompanyId"] = mfr_id
                response = post("/Contacts", post_data=post_data["contact"])
                post_data["service_object"]["CompanyId"] = post_data["contact"]["CompanyId"]
                response = post("/ServiceObjects", post_data=post_data["service_object"])
                if response.get("Id") in ["", None, 0]:
                    print(json.dumps(post_data["service_object"], indent=2))
                    print(json.dumps(response, indent=2))
                else:
                    update_company(bitrix_id, {"mfr_id": mfr_id, "mfr_service_object_id": response.get("Id")})
                    update_contact(bitrix_id, {"mfr_id": mfr_id, "mfr_service_object_id": response.get("Id")})
            else:
                update_company(bitrix_id, {"mfr_id": mfr_id})
        else:
            print(json.dumps(response, indent=2))
    else:
        post_data["Id"] = int(company_data.get('mfr_id'))
        response = put(f"/Companies({company_data.get('mfr_id')}L)", post_data=post_data)
        # TODO does not work yet. Response error: System.NullReferenceException: Object reference not set to an instance of an object
