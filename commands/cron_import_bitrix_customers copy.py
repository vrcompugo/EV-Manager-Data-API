from app.modules.importer.sources.bitrix24.customer import run_cron_import


def cron_import_bitrix_customers():
    run_cron_import()
