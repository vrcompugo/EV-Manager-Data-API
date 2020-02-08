

def run_import_by_model(model, remote_id=None, local_id=None):
    if model is None or model == "lead":
        from .lead import run_cron_import
        run_cron_import()


def run_export_by_model(model, remote_id=None, local_id=None):
    pass
