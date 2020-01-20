

def run_import_by_model(model, remote_id=None, local_id=None):

    if model is None or model == "customer":
        from .customer import run_import
        run_import()

    if model is None or model == "reseller":
        from .reseller import run_import
        run_import()

    if model is None or model == "survey":
        from .survey import run_import
        run_import(remote_id=remote_id, local_id=local_id)

    if model is None or model == "product":
        from .product import run_import
        run_import()

    if model is None or model == "offer":
        from .offer import run_import
        run_import(remote_id=remote_id, local_id=local_id)

    if model is None or model == "contract":
        from .contract import run_import
        run_import()

    if model is None or model == "lead_comment":
        from .lead_comment import run_import
        run_import(remote_id=remote_id)

    if model is not None and model == "lead_number":
        from .lead import run_export
        from app.models import Lead
        print("lead_number export", local_id)
        lead = Lead.query.filter(Lead.number == str(local_id)).first()
        print("found Lead", lead)
        if lead is not None:
            run_export(local_id=lead.id)


def run_export_by_model(model, remote_id=None, local_id=None):

    if model is None or model == "lead":
        from .lead import run_export
        run_export(remote_id=remote_id, local_id=local_id)
