import json

from app import db
from app.models import QuoteHistory
from app.modules.external.bitrix24.deal import get_deal, get_deals, update_deal
from app.modules.external.bitrix24.lead import get_lead, add_lead
from app.modules.quote_calculator.routes import quote_calculator_set_defaults, quote_calculator_add_history, quote_calculator_heating_pdf_action, quote_calculator_datasheets_pdf_action, quote_calculator_quote_summary_pdf_action, quote_calculator_contract_summary_pdf_action, quote_calculator_summary_pdf_action, quote_calculator_heatpump_autogenerate_pdf_action
from app.modules.quote_calculator.quote_data import calculate_heating_usage


def cron_heatpump_auto_quote_generator():
    deals = get_deals({
        "SELECT": "full",
        "FILTER[CATEGORY_ID]": 210,
        "FILTER[STAGE_ID]": "C210:NEW"
    }, force_reload=True)
    for deal in deals:
        if deal.get("contact_id") in [None, "", 0, "0"]:
            lead = get_lead(deal.get("unique_identifier"))
            update_deal(deal["id"], {
                "contact_id": lead.get("contact_id")
            })

    deals = get_deals({
        "SELECT": "full",
        "FILTER[CATEGORY_ID]": 210,
        "FILTER[STAGE_ID]": "C210:PREPAYMENT_INVOI"
    }, force_reload=True)
    for deal in deals:
        print("generate auto heating quote", deal["id"])
        try:
            if deal.get("unique_identifier") in [None, "", 0, "0"]:
                lead = add_lead({
                    "status_id": 22,
                    "contact_id": deal["contact_id"],
                })
                deal["unique_identifier"] = lead["id"]
                update_deal(deal["id"], {
                    "unique_identifier": lead["id"]
                })
            quote_data =  {
                "add_bluegen_storage": False,
                "additional_cloud_contract": None,
                "address": {},
                "assigned_user": {},
                "bankname": None,
                "iban": None,
                "bic": None,
                "birthdate": None,
                "has_bluegen_quote": False,
                "has_heating_quote": True,
                "has_old_pv": False,
                "has_pv_quote": False,
                "heating_quote_extra_options": []
            }
            fields = [
                "heating_quote_bathtub_count",
                "heating_quote_circulation_pump",
                "heating_quote_discount_euro",
                "heating_quote_discount_percent",
                "heating_quote_house_build",
                "heating_quote_house_type",
                "heating_quote_old_heating_build",
                "heating_quote_people",
                "heating_quote_radiator_count",
                "heating_quote_radiator_type",
                "heating_quote_shower_count",
                "heating_quote_sqm",
                "heating_quote_warm_water_type",
                "new_heating_type",
                "old_heating_type"
            ]
            for field in fields:
                quote_data[field] = deal.get(field)
            if quote_data["old_heating_type"] == "oil":
                quote_data["heating_quote_usage_oil"] = float(deal.get("heating_quote_usage_mixed"))
                quote_data["heating_quote_usage_old"] = 0
            else:
                quote_data["heating_quote_usage_old"] = float(deal.get("heating_quote_usage_mixed"))
                quote_data["heating_quote_usage_oil"] = 0
            quote_data = calculate_heating_usage(deal.get("unique_identifier"), quote_data)
            quote_calculator_set_defaults(deal.get("unique_identifier"))  # post /quote_calculator/${this.id}
            quote_calculator_add_history(deal.get("unique_identifier"), quote_data)  # put /quote_calculator/${this.id}
            quote_calculator_heating_pdf_action(deal.get("unique_identifier"))  # put /quote_calculator/${this.id}/heating_pdf
            quote_calculator_quote_summary_pdf_action(deal.get("unique_identifier"))  # put /quote_calculator/${this.id}/quote_summary_pdf
            quote_calculator_datasheets_pdf_action(deal.get("unique_identifier"))  # put /quote_calculator/${this.id}/datasheets_pdf
            quote_calculator_summary_pdf_action(deal.get("unique_identifier"))  # put /quote_calculator/${this.id}/summary_pdf
            quote_calculator_contract_summary_pdf_action(deal.get("unique_identifier"))  # put /quote_calculator/${this.id}/contract_summary_pdf
            data = quote_calculator_heatpump_autogenerate_pdf_action(deal.get("unique_identifier"))  # put /quote_calculator/${this.id}/heatpump_autogenerate_pdf
            if data.get("pdf_heatpump_auto_generate_link") not in [None, "", "0", 0, False]:
                update_deal(deal["id"], {
                    "pdf_heatpump_auto_generate_link": data.get("pdf_heatpump_auto_generate_link"),
                    "stage_id": "C210:EXECUTING"
                })
            else:
                move_to_manuell(deal["id"])
        except Exception as e:
            move_to_manuell(deal["id"])

def move_to_manuell(deal_id):
    update_deal(deal_id, {
        "stage_id": "C210:UC_BY30OU"
    })