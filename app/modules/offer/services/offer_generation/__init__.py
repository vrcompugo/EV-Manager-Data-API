from app import db
from app.models import Order
from .pv_offer import pv_offer_by_survey
from .roof_offer import roof_offer_by_survey
from .heater_offer import heater_offer_by_survey
from .storage_offer import storage_offer_by_survey


def automatic_offer_creation_by_survey(survey, old_data=None):

    from app.modules.offer.services.offer_generation import automatic_offer_creation_by_survey

    from app.modules.importer.sources.bitrix24.offer import run_export
    from app.modules.importer.sources.bitrix24.lead import run_status_update_export

    if ("offer_comment" not in survey.data or survey.data["offer_comment"] == ""):
        offer = None
        if "create_offer_pv" in survey.data and survey.data["create_offer_pv"]:
            print("offer creation pv")
            offer = pv_offer_by_survey(survey, old_data)
        if "create_offer_roof" in survey.data and survey.data["create_offer_roof"]:
            print("offer creation roof")
            offer = roof_offer_by_survey(survey, old_data)
        if "create_offer_heater" in survey.data and survey.data["create_offer_heater"]:
            print("offer creation heater")
            offer = heater_offer_by_survey(survey, old_data)
        if "create_offer_storage" in survey.data and survey.data["create_offer_storage"]:
            print("offer creation storage")
            offer = storage_offer_by_survey(survey, old_data)

        if survey.lead is not None and offer is not None:
            survey.lead.value = offer.total
            survey.lead.status = "offer_created"
            db.session.add(survey.lead)
            db.session.commit()
            run_status_update_export(local_id=survey.lead.id)


def generate_offer_by_order(order: Order):
    from .enpal_offer import enpal_offer_by_order
    from app.modules.importer.sources.bitrix24.order import run_offer_pdf_export
    if order is not None and order.category == "online Speichernachrüstung":
        print(f"generate offer for {order.id}")
        offer = enpal_offer_by_order(order)
        if offer.pdf is not None:
            public_link = offer.pdf.make_public()
            run_offer_pdf_export(local_id=order.id, public_link=public_link)
        else:
            print("pdf generation failed")
    else:
        print("order not found")
