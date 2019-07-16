

def run_import_by_model(model):

    if model is None or model == "customer":
        from .customer import run_import
        return run_import()
