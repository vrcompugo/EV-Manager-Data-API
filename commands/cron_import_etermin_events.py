from app.modules.importer.sources.etermin.calendar_event import run_cron_import


def cron_import_etermin_events():
    run_cron_import()
