from app.modules.importer.sources.bitrix24.task import run_cron_import


def cron_import_tasks():
    run_cron_import()
