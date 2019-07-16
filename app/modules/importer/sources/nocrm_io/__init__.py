

def run_import_by_model(model):

    if model is None or model == "reseller":
        from .reseller import run_import
        return run_import()

    if model is None or model == "lead":
        from .lead import run_import
        return run_import()
