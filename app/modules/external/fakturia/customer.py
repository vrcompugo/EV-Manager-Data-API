import json
from datetime import datetime
from schwifty import IBAN

from app import db
from app.modules.external.bitrix24.contact import get_contacts, update_contact as update_bitrix_contact
from app.modules.settings import set_settings, get_settings
from app.modules.external.bitrix24.contact import get_contact as get_bitrix_contact, get_contacts_by_changedate as get_bitrix_contacts_by_changedate
from app.modules.external.bitrix24.company import get_company as get_bitrix_company
from app.utils.error_handler import error_handler

from ._connector import get, post, put


def get_export_data(contact, company):
    salutation = "MR"
    if contact["salutation"] == "ms":
        salutation = "MRS"
    if contact["fakturia_owner"] in [None, ""]:
        if contact.get("first_name") not in [None]:
            contact["fakturia_owner"] = f'{contact["first_name"]} {contact["last_name"]}'
        else:
            contact["fakturia_owner"] = str(contact.get("last_name"))
    data = {
        "salutation": salutation,
        "firstName": contact["first_name"],
        "lastName": contact["last_name"],
        "locale": "de_DE",
        "taxRegion": "NATIONAL",
        "duePeriod": "14",
        "dueUnit": "DAY",
        "postalAddress": {
            "addressLine1": f"{contact['street']} {contact['street_nb']}",
            "zipCode": contact['zip'],
            "cityName": contact['city'],
            "country": "DE"
        },
        "billingAddress": {
            "addressLine1": f"{contact['street']} {contact['street_nb']}",
            "zipCode": contact['zip'],
            "cityName": contact['city'],
            "country": "DE"
        },
        "customFields": {
            "bitrix_id": contact['id']
        }
    }
    if contact["company"] not in [None, ""]:
        data["companyName"] = contact["company"]
        data["salutation"] = "COMPANY"
    iban = contact.get("fakturia_iban")
    if contact.get("fakturia_iban") in ["", None]:
        iban = contact.get("iban")
    if iban not in ["", None]:
        try:
            iban = IBAN(iban)
            bic = iban.bic.compact
            iban = iban.compact
            data["bankAccountIban"] = iban
            data["bankAccountBic"] = bic
            data["bankAccountOwner"] = contact["fakturia_owner"]
            if contact.get("fakturia_owner") in ["", None]:
                data["bankAccountOwner"] = f'{contact["first_name"]} {contact["last_name"]}'
        except Exception as e:
            print("error iban", contact)
    if company is not None:
        data["companyName"] = company["title"]
        data["salutation"] = "COMPANY"
    if contact.get("phone", None) is not None and len(contact.get("phone")) > 0:
        data["phone1"] = contact.get("phone")[0]["VALUE"]
    if contact.get("email", None) is not None and len(contact.get("email")) > 0:
        data["email"] = contact.get("email")[0]["VALUE"]
    return data


def run_cron_export():
    config = get_settings("external/fakturia")
    print("export customer fakturia")
    if config is None:
        print("no config for fakturia import")
        return None

    import_time = datetime.now()
    contacts = get_contacts({
        "SELECT": "full",
        "filter[>DATE_MODIFY]": str(config.get("last_contact_export_time", "2021-01-20 00:00:00"))
    }, force_reload=True)
    if contacts is None:
        print("contacts could not be loaded")
        return
    for contact in contacts:

        export_contact(contact)
    config = get_settings("external/fakturia")
    if config is not None:
        config["last_contact_export_time"] = import_time.astimezone().isoformat()
    set_settings("external/fakturia", config)


def export_contact(contact, force=False):
    company = None
    if contact.get("company_id", 0) is not None and int(contact.get("company_id", 0)) > 0:
        company = get_bitrix_company(int(contact.get("company_id")))

    if contact.get("fakturia_number") in ["", None]:
        export_data = get_export_data(contact, company)
        if export_data is None or "email" not in export_data:
            print(contact, export_data)
            print("no export data")
            return
        customer_data = post(f"/Customers", post_data=export_data)
        print(json.dumps(customer_data, indent=2))
        if customer_data is not None and "customerNumber" in customer_data:
            contact["fakturia_number"] = customer_data["customerNumber"]
            put(f"/Customers/{contact.get('fakturia_number')}/CustomFields", post_data=export_data["customFields"])
            update_bitrix_contact(contact["id"], {
                "fakturia_number": customer_data["customerNumber"]
            })
            # create sepa mandete
            if contact.get("sepa_mandate_since") not in [None, "None", ""]:
                post(f"/Customers/{contact.get('fakturia_number')}/SepaDebitMandates", post_data={
                    "debitType": "BASIS_LASTSCHRIFT",
                    "mandateType": "RECUR",
                    "status": "ACTIVE",
                    "created": datetime.now().strftime("%Y-%m-%d"),
                    "issueDate": contact.get('sepa_mandate_since')
                })
            print(contact["id"])
        else:
            print(json.dumps(customer_data, indent=2))
    else:
        if True:
            export_data = get_export_data(contact, company)
            print(contact["id"], "export", contact.get("date_modify"))
            customer_data = put(f"/Customers/{contact.get('fakturia_number')}", post_data=export_data)
            print(export_data, contact)
            if contact.get("sepa_mandate_since") not in [None, "None", ""]:
                mandates = get(f"/Customers/{contact.get('fakturia_number')}/SepaDebitMandates")
                if mandates is not None and len(mandates) == 0:
                    post(f"/Customers/{contact.get('fakturia_number')}/SepaDebitMandates", post_data={
                        "debitType": "BASIS_LASTSCHRIFT",
                        "mandateType": "RECUR",
                        "status": "ACTIVE",
                        "created": datetime.now().strftime("%Y-%m-%d"),
                        "issueDate": contact.get('sepa_mandate_since')[:10]
                    })
        else:
            print(contact["id"], "no export", contact.get("date_modify"))

