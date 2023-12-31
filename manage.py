import os
import json
import time
from time import sleep
import unittest
from flask_migrate import Migrate, MigrateCommand, upgrade
from flask_script import Manager, prompt_bool
import sqlalchemy as sa

from app import create_app, db
from app.blueprint import register_blueprints

app = create_app(os.getenv('ENVIRONMENT') or 'dev')
register_blueprints(app)

app.app_context().push()

manager = Manager(app)

migrate = Migrate(app, db)

manager.add_command('db', MigrateCommand)


@manager.command
def run():
    upgrade()
    app.run(host="0.0.0.0")


@manager.command
def install():
    upgrade()
    from app.modules.user import install as user_install
    user_install()


@manager.command
def update_role_permissions():
    from app.modules.user import update_role_permissions
    update_role_permissions()


@manager.command
def check_contacts():
    from app.modules.external.bitrix24.contact import get_contacts
    contacts = get_contacts({
        "SELECT": "full",
        "filter[>DATE_MODIFY]": "2021-11-08 13:00:00"
    })
    print(json.dumps(contacts, indent=2))


@manager.command
def sign_date_test():
    import datetime
    from app.modules.external.bitrix24.lead import update_lead, get_lead
    print("sign_date_test")
    lead_data = {}
    lead_data["order_sign_date"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S-01:00")
    # lead_data["order_sign_date"] = str(datetime.datetime.now())
    print(lead_data)
    update_lead("30162", lead_data)


@manager.command
def rerun_auto_assign_lead_to_user():
    import datetime
    from app.modules.user import auto_assign_lead_to_user
    from app.modules.external.bitrix24.lead import get_leads
    leads = get_leads({
        "filter[>ACTIVITY_DATE]": "2021-11-22",
        "filter[=ASSIGNED_BY_ID]": "344"
    })
    for lead in leads:
        print(lead.get("id"))
        auto_assign_lead_to_user(lead.get("id"))


@manager.command
def get_test_deal():
    from app.modules.external.bitrix24.deal import get_deal, get_deals, list_request, update_deal
    from app.modules.external.bitrix24.lead import get_leads, get_lead
    from app.modules.external.bitrix24.task import get_tasks
    from app.modules.external.bitrix24.drive import get_file
    from app.modules.external.bitrix24.contact import get_contacts, get_contact
    print(json.dumps(get_file(8050093), indent=2))
    return
    #update_deal("153505", { "STAGE_ID": "C15:4" })
    #return
    deals = get_deals({
        "filter[!CATEGORY_ID]": "68",
        "filter[STAGE_ID]": "C68:PREPARATION",
        "SELECT": "full"
    }, force_reload=True)
    for deal in deals:
        print(deal.get("id"), deal.get("category_id"))
    print(len(deals))


@manager.command
def send_test_enbw_contract():
    from app.modules.external.enbw.contract import send_contract
    send_contract("C2205307037")


@manager.command
def run_remove_double_follow_contracts():
    from app.modules.cloud.services.contract import remove_double_follow_contracts
    remove_double_follow_contracts()



@manager.command
def add_cloud_values():
    from app.modules.cloud.services.contract import add_cloud_values
    add_cloud_values()


@manager.command
def get_test_insign():
    from app.modules.external.insign.signature import download_file
    content = download_file("3fe264f4a2497fba4f6e59e", 3007910)
    if isinstance(content, dict):
        return content
    with open("lsdk.pdf", "wb") as fh:
        fh.write(content)


@manager.command
def test_special():
    from app.models import OfferV2, Order, ImportIdAssociation
    from app.modules.importer.sources.bitrix24.order import run_export as run_order_export
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
                run_order_export(local_id=order.id)


@manager.command
def get_test_recreate_quote():
    from app.modules.quote_calculator.cron import recreate_quote
    recreate_quote(96881, create_new_quote=True)


@manager.command
def get_test_missing_values_deal():
    from app.modules.external.bitrix24.deal import get_deal, set_missing_values
    from app.modules.external.bitrix24.lead import get_lead
    print(json.dumps(set_missing_values(get_deal(137757)), indent=2))


@manager.option("-i", "--id", dest='deal_id', default=None)
def run_fakturia_deal_export(deal_id):
    from app.modules.external.fakturia.deal import run_export_by_id
    if deal_id is None:
        print("no deal id")
        return
    run_export_by_id(deal_id)


@manager.command
def create_cloud_contract_deals():
    from app.modules.external.bitrix24.deal import get_deals, add_deal, get_deal, update_deal
    from app.modules.cloud.cloud2_routes import get_invoce_list
    from app.modules.order.models.order import Order
    from app.modules.cloud.services.contract import normalize_contract_number, get_contract_data, get_annual_statement_data
    from app.modules.settings import get_settings
    from app.models import Contract

    config = get_settings(section="external/bitrix24")
    deals = get_deals({
        "SELECT": "full",
        "filter[CATEGORY_ID]": 126
    })
    existing_deals = []
    for deal in deals:
        if deal.get('contract_number') in [None, ""]:
            print(deal.get("title"))
            data = {
                config["deal"]["fields"]["contract_number"]: deal.get("title")
            }
            update_deal(deal.get("id"), data)
        if deal.get('contract_number') not in existing_deals:
            if deal.get('contact_id') in [None, 0, "0"] or deal.get('cloud_number') in [None, 0, "0"]:
                try:
                    contract_data = get_contract_data(deal.get('contract_number'))
                    deal_data = {
                        "contact_id": contract_data.get("contact_id"),
                        config["deal"]["fields"]["cloud_number"]: contract_data["cloud"].get("cloud_number")
                    }
                    print(deal.get("id"), deal_data)
                    update_deal(deal.get("id"), deal_data)
                except Exception as e:
                    pass
            existing_deals.append(deal.get('contract_number'))
        else:
            print("double", deal.get('contract_number'))
    '''
    year = 2021
    contracts = db.session.query(Contract)\
        .filter(Contract.begin >= f"{year}-01-01") \
        .filter(Contract.begin <= f"{year}-12-31") \
        .order_by(Contract.contract_number.desc())
    for contract in contracts:
        if contract.contract_number not in existing_deals:
            try:
                contract_data = get_contract_data(contract.contract_number)
                deal_data = {
                    "contact_id": contract_data.get("contact_id"),
                    config["deal"]["fields"]["cloud_number"]: contract_data["cloud"].get("cloud_number"),
                    config["deal"]["fields"]["contract_number"]: contract.contract_number,
                    "title": contract.contract_number,
                    "category_id": 126,
                    "stage_id": "C126:NEW"
                }
                print(contract.contract_number )
                add_deal(deal_data)
            except Exception as e:
                print(e)
    '''

@manager.command
def create_cloud_contract_deals2():
    from app.modules.external.bitrix24.deal import get_deals, add_deal, get_deal, update_deal
    from app.modules.cloud.cloud2_routes import get_invoce_list
    from app.modules.order.models.order import Order
    from app.modules.cloud.services.contract import normalize_contract_number, get_contract_data, get_annual_statement_data
    from app.modules.settings import get_settings
    from app.models import Contract

    config = get_settings(section="external/bitrix24")
    deals = get_deals({
        "SELECT": "full",
        "filter[CATEGORY_ID]": 126
    }, force_reload=True)
    existing_deals = []
    for deal in deals:
        if deal.get('contract_number') not in existing_deals:
            existing_deals.append(deal.get('contract_number'))
        else:
            print("double", deal.get('contract_number'))

    year = 2021
        #.filter(Contract.begin <= f"{year}-12-31") \
    contracts = db.session.query(Contract)\
        .filter(Contract.begin.is_(None)) \
        .order_by(Contract.contract_number.desc())
    for contract in contracts:
        if contract.contract_number not in existing_deals:
            print(contract.contract_number)
            try:
                contract_data = get_contract_data(contract.contract_number)
                deal_data = {
                    "contact_id": contract_data.get("contact_id"),
                    config["deal"]["fields"]["cloud_number"]: contract_data["cloud"].get("cloud_number"),
                    config["deal"]["fields"]["contract_number"]: contract.contract_number,
                    "title": contract.contract_number,
                    "category_id": 126,
                    "stage_id": "C126:NEW"
                }
                add_deal(deal_data)
            except Exception as e:
                deal_data = {
                    config["deal"]["fields"]["contract_number"]: contract.contract_number,
                    "title": contract.contract_number,
                    "category_id": 126,
                    "stage_id": "C126:UC_CQNYI7"
                }
                add_deal(deal_data)


@manager.command
def generate_cloud_contract_reports():
    from app.modules.external.bitrix24.deal import get_deals, get_deal
    from app.modules.cloud.services.contract import generate_annual_report

    deals = get_deals({
        "SELECT": "full",
        "filter[CATEGORY_ID]": 126,
        "filter[STAGE_ID]": "C126:PREPAYMENT_INVOICE"
    })
    for deal in deals:
        print(deal.get("contract_number"))
        generate_annual_report(deal.get("contract_number"), "2021")


@manager.command
def find_credit_memo_bugs():
    from app.modules.cloud.services.contract import find_credit_memo_bugs
    find_credit_memo_bugs()


@manager.command
def fix_legacy_copy_tab_pdf():
    from app.modules.quote_calculator.routes import fix_legacy_copy_tab_pdf
    fix_legacy_copy_tab_pdf()


@manager.command
def run_legacy_folder_creation():
    from app.modules.external.bitrix24.drive import run_legacy_folder_creation
    run_legacy_folder_creation()


@manager.command
def run_cron_export_anual_payments():
    from app.modules.external.fakturia.deal import run_cron_export_anual_payments
    run_cron_export_anual_payments()


@manager.command
def run_mfr_subscriptor():
    from app.modules.external.mfr.amqp import run_mfr_amqp_messaging_subscriptor
    run_mfr_amqp_messaging_subscriptor()


@manager.command
def export_mfr_task_by_bitrix_id():
    from app.modules.external.mfr.task import export_by_bitrix_id
    export_by_bitrix_id(283384)


@manager.option("-s", "--section", dest='section', default=None)
def cron(section):
    from app.modules.cron import cron
    cron(section)


@manager.option("-m", "--module", dest='module', default=None)
@manager.option("-s", "--source", dest='source', default=None)
@manager.option("-l", "--local_id", dest='local_id', default=None)
@manager.option("-r", "--remote_id", dest='remote_id', default=None)
@manager.option("-y", "--y", dest='yes', default=None)
def import_remote_data(yes, source, module, local_id, remote_id):
    if source is None:
        print("No source parameter given -s or --source")
        return
    if yes is not None or prompt_bool(
            "Are you sure you want to import from remote source: {}".format(source)):
        from app.modules.importer.import_services import import_by_source_module
        import_by_source_module(source=source, model=module, local_id=local_id, remote_id=remote_id)


@manager.option("-m", "--module", dest='module', default=None)
@manager.option("-s", "--source", dest='source', default=None)
@manager.option("-l", "--local_id", dest='local_id', default=None)
@manager.option("-r", "--remote_id", dest='remote_id', default=None)
@manager.option("-y", "--y", dest='yes', default=None)
def export_remote_data(yes, source, module, local_id, remote_id):
    if source is None:
        print("No source parameter given -s or --source")
        return
    if yes is not None or prompt_bool(
            "Are you sure you want to import from remote source: {}".format(source)):
        from app.modules.importer.export_services import export_by_source_module
        export_by_source_module(source=source, model=module, local_id=local_id, remote_id=remote_id)


@manager.command
@manager.option("-t", "--test", dest='test_name', default=None)
def test(test_name=None):
    """Runs the unit tests."""
    if test_name is not None:
        tests = unittest.TestLoader().discover('test', pattern=f'test_{test_name}.py')
    else:
        tests = unittest.TestLoader().discover('test', pattern='test*.py')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    if result.wasSuccessful():
        return 0
    return 1


@manager.command
def run_smartmetest():
    from app.modules.external.smartme.powermeter_measurement import get_device_by_datetime
    print(get_device_by_datetime("191760", "2023-01-01"))


@manager.command
def run_sherpa_import2():
    from app.modules.external.sherpa.contract import import_contracts_for_anual_report
    import_contracts_for_anual_report()


@manager.command
def run_get_task_test():
    from app.modules.external.bitrix24.task import get_task
    data = {
        "comment_files": []
    }
    task_data = get_task(428051)
    if task_data.get("comments") is not None:
        for comment in task_data.get("comments"):
            if comment.get("ATTACHED_OBJECTS") not in [None, "", 0]:
                for key in comment.get("ATTACHED_OBJECTS").keys():
                    data["comment_files"].append(comment.get("ATTACHED_OBJECTS")[key])
    print(json.dumps(data, indent=2))


@manager.command
def run_cron_follow_cloud_quote_test():
    from app.modules.quote_calculator.cron import cron_follow_cloud_quote_test
    cron_follow_cloud_quote_test()


@manager.command
def run_fix_legacy_solar_edge_links():
    from app.modules.quote_calculator.routes import fix_legacy_solar_edge_links
    fix_legacy_solar_edge_links()


@manager.command
@manager.option("-kw", "--kw", dest='kw', default=0)
def run_generate_weekly_invoice_bundles(kw):
    from app.modules.invoice import cron_generate_weekly_invoice_bundles
    cron_generate_weekly_invoice_bundles(offset_weeks=int(kw))


@manager.command
def run_process_existing_enbw_contracts():
    from app.modules.external.enbw.contract import process_existing_enbw_contracts
    process_existing_enbw_contracts()


if __name__ == '__main__':
    sa.orm.configure_mappers()
    manager.run()
