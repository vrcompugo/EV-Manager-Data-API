

def cron():

    from .sources.bitrix24.reseller import run_import
    run_import()

    from .sources.bitrix24.lead import run_cron_import
    run_cron_import()

    from .sources.bitrix24.order import run_cron_import
    run_cron_import()

    from .sources.daa.lead import run_cron_import
    run_cron_import()

    from .sources.bitrix24.lead import run_cron_export
    run_cron_export()
