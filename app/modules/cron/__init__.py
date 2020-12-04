import datetime
import json
from app.modules.external.bitrix24.deal import get_deal
from app.utils.error_handler import error_handler


def cron(section=None):
    if section == "productive" or section == "import_leads_aroundhome":
        from app.modules.external.aroundhome.deal import run_cron_import
        print("cron", "import_leads_aroundhome")
        run_cron_import()

    if section == "productive" or section == "import_leads_daa":
        from app.modules.external.daa.deal import run_cron_import
        print("cron", "import_leads_daa")
        run_cron_import()

    if section == "productive" or section == "import_leads_hausfrage":
        from app.modules.external.hausfrage.deal import run_cron_import
        print("cron", "import_leads_hausfrage")
        run_cron_import()

    if section == "productive" or section == "import_leads_senec":
        from app.modules.external.senec.deal import run_cron_import
        print("cron", "import_leads_senec")
        run_cron_import()

    if section == "productive" or section == "import_leads_wattfox":
        from app.modules.external.wattfox.deal import run_cron_import
        print("cron", "import_leads_wattfox")
        run_cron_import()

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
