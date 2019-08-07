

def cron():
    from .sources.nocrm_io.lead import run_import
    run_import(minutes=10)
