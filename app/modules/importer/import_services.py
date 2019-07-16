

def import_by_source_module(source, model):

    if source == "data.efi-strom.de":
        from .sources.data_efi_strom import run_import_by_model
        run_import_by_model(model)

    if source == "nocrm.io":
        from .sources.nocrm_io import run_import_by_model
        run_import_by_model(model)

    if source == "orgamaxx":
        from .sources.orgamaxx import run_import_by_model
        run_import_by_model(model)

    return None
