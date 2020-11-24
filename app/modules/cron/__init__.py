import datetime
import json
from app.modules.external.bitrix24.deal import get_deal


def cron(section=None):

    if datetime.datetime.now() <= datetime.datetime(2020, 11, 1, 9, 0, 0):
        print("cron outside of start", section)
        return section

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

    if section == "productive" or section == "dublicate_check":
        from app.modules.external.bitrix24.deal import run_dublicate_check
        print("cron", "dublicate_check")
        run_dublicate_check()
