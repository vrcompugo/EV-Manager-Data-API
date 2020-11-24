

def run_import_by_model(model, remote_id=None, local_id=None):
    pass

def run_export_by_model(model, remote_id=None, local_id=None):

    if model is None or model == "customer":
        from .customer import run_cron_export
        run_cron_export()
