

def run_import_by_model(model):

    if model is None or model == "customer":
        from .customer import run_import
        return run_import()

    if model is None or model == "reseller":
        from .reseller import run_import
        return run_import()

    if model is None or model == "survey":
        from .survey import run_import
        return run_import()

    if model is None or model == "product":
        from .product import run_import
        return run_import()

    if model is None or model == "offer":
        from .offer import run_import
        return run_import()

    if model is None or model == "contract":
        from .contract import run_import
        return run_import()
