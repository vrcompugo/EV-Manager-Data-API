

def cron():
    from .sources.nocrm_io.lead import run_import
    run_import(minutes=10)

    from .sources.data_efi_strom.reseller import run_import as run_import_reseller
    run_import_reseller()

    from .sources.nocrm_io.reseller import run_import as run_import_reseller2
    run_import_reseller2()
