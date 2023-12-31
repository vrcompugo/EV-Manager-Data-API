from app.exceptions import ApiException
import datetime
import json
import traceback
from app.modules.external.bitrix24.deal import get_deal
from app.utils.error_handler import error_handler


def cron(section=None):
    if section == "productive" or section == "user_cache_refresh":
        from app.modules.external.bitrix24.user import cron_refresh_users
        print("cron", "user_cache_refresh")
        try:
            cron_refresh_users()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "import_leads_aroundhome":
        from app.modules.external.aroundhome.deal import run_cron_import
        print("cron", "import_leads_aroundhome")
        try:
            run_cron_import()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "import_leads_daa":
        from app.modules.external.daa.deal import run_cron_import
        print("cron", "import_leads_daa")
        try:
            run_cron_import()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "import_leads_senec":
        from app.modules.external.senec.deal import run_cron_import
        print("cron", "import_leads_senec")
        try:
            run_cron_import()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "auto_assign_leads":
        from app.modules.external.bitrix24.lead import run_cron_auto_assign_leads
        print("cron", "auto_assign_leads")
        try:
            run_cron_auto_assign_leads()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "import_leads_wattfox":
        from app.modules.external.wattfox.deal import run_cron_import
        print("cron", "import_leads_wattfox")
        try:
            run_cron_import()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "import_power_meter_values":
        from app.modules.external.smartme.powermeter_measurement import run_cron_import
        print("cron", "import_power_meter_values")
        try:
            run_cron_import()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "bennemann_lead_convert":
        from app.modules.external.bitrix24.lead import run_bennemann_lead_convert
        try:
            run_bennemann_lead_convert()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "extern_lead_convert":
        from app.modules.external.bitrix24.lead import run_extern_lead_convert
        try:
            run_extern_lead_convert()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "add_missing_deal_values":
        from app.modules.external.bitrix24.deal import run_cron_add_missing_values
        try:
            run_cron_add_missing_values()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "copy_cloud_deal_values":
        from app.modules.cloud.services.deal import cron_copy_cloud_deal_values
        try:
            cron_copy_cloud_deal_values()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "bitrix_user_import":
        from app.modules.importer.sources.bitrix24.reseller import run_import
        try:
            run_import()
        except Exception as e:
            error_handler()

        from app.modules.importer.sources.bitrix24.user import run_cron_import
        try:
            run_cron_import()
        except Exception as e:
            error_handler()

    if section == "obsolete-fakturia" or section == "fakturia_customer_export":  # fakturia was replaced by odoo
        from app.modules.external.fakturia.customer import run_cron_export
        try:
            run_cron_export()
        except Exception as e:
            error_handler()

    if section == "obsolete-fakturia" or section == "fakturia_deal_export":  # fakturia was replaced by odoo
        from app.modules.external.fakturia.deal import run_cron_export
        try:
            run_cron_export()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "auto_assignment_facebook_leads":
        from app.modules.lead.lead_services import auto_assignment_facebook_leads
        try:
            auto_assignment_facebook_leads()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "mfr_task_export":
        from app.modules.external.mfr.task import run_cron_export
        try:
            run_cron_export()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "etermin_import":
        from app.modules.external.etermin.appointment import import_new_appointments
        try:
            import_new_appointments()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "etermin_export":
        from app.modules.external.etermin.appointment import export_appointments
        try:
            export_appointments()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "folder_creation":
        from app.modules.external.bitrix24.drive import run_cron_folder_creation
        try:
            run_cron_folder_creation()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "heating_folder_creation":
        from app.modules.external.bitrix24.drive import run_cron_heating_folder_creation
        try:
            run_cron_heating_folder_creation()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "external_company_folder_creation":
        from app.modules.external.bitrix24.drive import run_cron_external_company_folder_creation
        try:
            run_cron_external_company_folder_creation()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "find_stuck_orders":
        from app.models import OfferV2, Order, ImportIdAssociation
        try:
            offers = OfferV2.query.filter(OfferV2.is_sent.is_(True)).all()
            for offer in offers:
                orders = Order.query.filter(Order.offer_id == offer.id).all()
                for order in orders:
                    link = ImportIdAssociation.query\
                        .filter(ImportIdAssociation.local_id == order.id)\
                        .filter(ImportIdAssociation.source == 'bitrix24')\
                        .filter(ImportIdAssociation.model == 'Order')\
                        .first()
                    if link is None:
                        print("order", order.id)
                        raise Exception("stuck order found")
        except Exception as e:
            error_handler()

    if section == "productive" or section == "mfr_import":
        from app.modules.external.mfr.amqp import run_cron_import
        try:
            run_cron_import()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "split_cloud_contract":
        from app.modules.cloud.services.deal import cron_split_cloud_contract
        try:
            cron_split_cloud_contract()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "mein_portal_initial_documents":
        from app.modules.cloud.services.deal import cron_mein_portal_initial_documents
        try:
            cron_mein_portal_initial_documents()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "heatpump_auto_quote_generator":
        from app.modules.quote_calculator.cron import cron_heatpump_auto_quote_generator
        try:
            cron_heatpump_auto_quote_generator()
        except Exception as e:
            error_handler()

    if section == "productive" or section == "cron_follow_cloud_quote":
        from app.modules.quote_calculator.cron import cron_follow_cloud_quote
        try:
            cron_follow_cloud_quote()
        except Exception as e:
            print(traceback.format_exc())

    if section == "inactive" or section == "bsh_quote_numbers":
        from app.modules.quote_calculator.cron import cron_bsh_quote_numbers
        try:
            cron_bsh_quote_numbers()
        except Exception as e:
            error_handler()

    if section == "obsolete-fakturia" or section == "cron_transfer_fakturia_annual_invoice":  # fakturia was replaced by odoo
        from app.modules.cloud.services.contract import cron_transfer_fakturia_annual_invoice
        try:
            cron_transfer_fakturia_annual_invoice()
        except Exception as e:
            error_handler()

    if section == "cron_bitrix_file_sync":
        from app.modules.file.file_services import cron_bitrix_export_item
        try:
            cron_bitrix_export_item()
        except Exception as e:
            print(traceback.format_exc())

    if section == "productive" or section == "cron_generate_weekly_invoice_bundles":
        from app.modules.invoice import cron_generate_weekly_invoice_bundles
        try:
            cron_generate_weekly_invoice_bundles()
        except Exception as e:
            print(traceback.format_exc())

    if section == "productive" or section == "cron_update_contract_status":
        from app.modules.external.enbw.contract import cron_update_contract_status
        try:
            cron_update_contract_status()
        except Exception as e:
            print(traceback.format_exc())

