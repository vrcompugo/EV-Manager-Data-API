

def import_by_source_module(source, model):
    if source == "data.efi-strom.de":
        if model == "customer":
            from .sources.data_efi_strom.customer import run_import
            return run_import()
        if model == "reseller":
            from .sources.data_efi_strom.reseller import run_import
            return run_import()
        if model == "survey":
            from .sources.data_efi_strom.survey import run_import
            return run_import()
        if model == "product":
            from .sources.data_efi_strom.product import run_import
            return run_import()
        if model == "offer":
            from .sources.data_efi_strom.offer import run_import
            return run_import()
        if model == "contract":
            from .sources.data_efi_strom.contract import run_import
            return run_import()
    return None
