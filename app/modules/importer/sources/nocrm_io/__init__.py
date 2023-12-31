

def run_import_by_model(model, remote_id=None, local_id=None):

    if model is None or model == "reseller":
        from .reseller import run_import
        run_import()

    if model is None or model == "lead":
        from .lead import run_import
        run_import(remote_id=remote_id)


def run_export_by_model(model, remote_id=None, local_id=None):

    if model is None or model == "lead":
        from .lead import run_export
        run_export(remote_id=remote_id, local_id=local_id)
