
from app.utils.error_handler import error_handler


def cron():

    from .sources.bitrix24.reseller import run_import
    try:
        run_import()
    except Exception as e:
        error_handler()

    from .sources.bitrix24.customer import run_cron_import
    try:
        run_cron_import()
    except Exception as e:
        error_handler()

    from .sources.bitrix24.lead import run_cron_import
    try:
        run_cron_import()
    except Exception as e:
        error_handler()

    from .sources.bitrix24.order import run_cron_import
    try:
        run_cron_import()
    except Exception as e:
        error_handler()

    from .sources.daa.lead import run_cron_import
    try:
        run_cron_import()
    except Exception as e:
        error_handler()

    from .sources.wattfox.lead import run_cron_import
    try:
        run_cron_import()
    except Exception as e:
        error_handler()

    from .sources.aroundhome.lead import run_cron_import
    try:
        run_cron_import()
    except Exception as e:
        error_handler()

    from .sources.bitrix24.lead import run_cron_export
    try:
        run_cron_export()
    except Exception as e:
        error_handler()

    from .sources.bitrix24.user import run_cron_import
    try:
        run_cron_import()
    except Exception as e:
        error_handler()
