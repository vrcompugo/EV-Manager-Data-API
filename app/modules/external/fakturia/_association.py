from app.modules.external._association import find_log as find_log_base, log_item as log_item_base


def find_log(model, identifier, domain_raw=None):
    return find_log_base("fakturia", model, identifier, domain_raw)


def log_item(model, identifier, domain_raw=None):
    return log_item_base("fakturia", model, identifier, domain_raw)
