import datetime
import dateutil.relativedelta
import json
from dateutil.parser import parse

from app import db
from app.models import QuoteHistory
from app.modules.offer.models.offer_v2 import OfferV2
from app.modules.settings import get_settings, set_settings
from app.utils.error_handler import error_handler
from app.modules.external.bitrix24.deal import get_deal, get_deals, update_deal
from app.modules.external.bitrix24.lead import get_lead, add_lead
from app.modules.external.bitrix24.task import add_task
from app.modules.quote_calculator.routes import quote_calculator_set_defaults, \
    quote_calculator_add_history, quote_calculator_heating_pdf_action, \
    quote_calculator_datasheets_pdf_action, quote_calculator_quote_summary_pdf_action, \
    quote_calculator_contract_summary_pdf_action, quote_calculator_summary_pdf_action, \
    quote_calculator_heatpump_autogenerate_pdf_action, quote_calculator_cloud_pdfs_action
from app.modules.quote_calculator.quote_data import calculate_heating_usage


def cron_heatpump_auto_quote_generator():
    deals = get_deals({
        "SELECT": "full",
        "FILTER[CATEGORY_ID]": 210,
        "FILTER[STAGE_ID]": "C210:NEW"
    }, force_reload=True)
    if deals is None:
        print("deals could not be loaded")
        return
    for deal in deals:
        if deal.get("contact_id") in [None, "", 0, "0"]:
            lead = get_lead(deal.get("unique_identifier"))
            if lead is not None:
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
                quote_data["heating_quote_usage_oil"] = float(deal.get("heating_quote_usage_oil"))
                quote_data["heating_quote_usage_old"] = float(deal.get("heating_quote_usage_oil")) * 10
            elif quote_data["old_heating_type"] == "gas":
                quote_data["heating_quote_usage_old"] = float(deal.get("heating_quote_usage_gas"))
            elif quote_data["old_heating_type"] == "pellez":
                quote_data["heating_quote_usage_pellets"] = float(deal.get("heating_quote_usage_pellets"))
                quote_data["heating_quote_usage_old"] = (float(deal.get("heating_quote_usage_pellets")) / 1000) * 4.9
            else:
                quote_data["heating_quote_usage_old"] = float(deal.get("heating_quote_usage_mixed"))
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
            error_handler()


def move_to_manuell(deal_id):
    update_deal(deal_id, {
        "stage_id": "C210:UC_BY30OU"
    })


def cron_bsh_quote_numbers():
    print("cron_bsh_quote_numbers")
    config = get_settings("bsh_quote_numbers")
    now = datetime.datetime.now()
    last_excecute = datetime.datetime(now.year, now.month, 1)
    print(last_excecute)
    if config.get("last_excecute") is None:
        config["last_excecute"] = datetime.datetime(2022, 4, 1)
    else:
        config["last_excecute"] = parse(config["last_excecute"])
    diff_months = (last_excecute.year - config["last_excecute"].year) * 12 + last_excecute.month - config["last_excecute"].month
    for i in range(diff_months):
        range_start = last_excecute - dateutil.relativedelta.relativedelta(months=diff_months - i)
        range_end = str(last_excecute - dateutil.relativedelta.relativedelta(months=diff_months - i - 1))
        title = f"BSH-Angebote für {range_start.month} {range_start.year}:\n"
        description = f"BSH-Angebote für {range_start.month} {range_start.year}:\n"
        range_start = str(range_start)

        result = db.session.execute(f"select customer_id, count(offer_v2.id) as quote_per_customer from offer_v2 where reseller_id = 92 and datetime >= '{range_start}' and datetime < '{range_end}' group by  customer_id")
        description = description + f"Eindeutige Kunden mit Angebots: {result.rowcount}\n"
        result = db.session.execute(f"select customer_id from offer_v2 where reseller_id = 92 and datetime >= '{range_start}' and datetime < '{range_end}'")
        description = description + f"Angebote gesamt: {result.rowcount}\n"
        print(description)
        add_task({
            "fields[TITLE]": title,
            "fields[DESCRIPTION]": description,
            "fields[RESPONSIBLE_ID]": 33,
            "fields[DEADLINE]": str(datetime.datetime.now() + datetime.timedelta(days=14))
        })
    config = json.loads(json.dumps(get_settings("bsh_quote_numbers")))
    config["last_excecute"] = str(last_excecute)
    set_settings("bsh_quote_numbers", config)


def cron_follow_cloud_quote():
    deals = get_deals({
        "SELECT": "full",
        "FILTER[CATEGORY_ID]": 220,
        "FILTER[STAGE_ID]": "C220:UC_38IJOQ"
    }, force_reload=True)
    for deal in deals:
        recreate_quote(deal["id"])


def recreate_quote(deal_id):
    deal = get_deal(deal_id)
    if deal.get("unique_identifier") in [None, ""]:
        lead = add_lead({
            "contact_id": deal.get("contact_id"),
            "status_id": "UC_5NR721"
        })
        update_deal(deal.get("id"), {
            "unique_identifier": lead.get("id")
        })
    else:
        lead = get_lead(deal.get("unique_identifier"))
    offer_v2 = OfferV2.query.filter(OfferV2.number == deal.get("cloud_number")).first()
    data = json.loads(json.dumps(offer_v2.data))
    data["has_pv_quote"] = True
    data["document_style"] = ""
    quote_calculator_add_history(lead["id"], data)
    quote_calculator_cloud_pdfs_action(lead["id"])
    history = QuoteHistory.query.filter(QuoteHistory.lead_id == lead["id"]).order_by(QuoteHistory.datetime.desc()).first()
    update_deal(deal.get("id"), {
        "cloud_follow_quote_link": history.data["calculated"]["pdf_link"]
    })