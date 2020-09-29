from app.modules.importer.sources.etermin.customer import run_cron_export


def cron_export_etermin_customers():
    run_cron_export()
