
def export_by_source_module(source, model, remote_id=None, local_id=None):
    if source == "data.efi-strom.de":
        from .sources.data_efi_strom import run_export_by_model
        run_export_by_model(model=model, remote_id=remote_id, local_id=local_id)

    if source == "nocrm.io":
        from .sources.nocrm_io import run_export_by_model
        run_export_by_model(model=model, remote_id=remote_id, local_id=local_id)

    if source == "orgamaxx":
        from .sources.orgamaxx import run_export_by_model
        run_export_by_model(model=model, remote_id=remote_id, local_id=local_id)

    if source == "bitrix24":
        from .sources.bitrix24 import run_export_by_model
        run_export_by_model(model=model, remote_id=remote_id, local_id=local_id)

    return None

