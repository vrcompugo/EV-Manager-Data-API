from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model

from .models.import_id_association import ImportIdAssociation, ImportIdAssociationSchema


def import_by_source_module(source, model, remote_id=None, local_id=None):
    if source == "data.efi-strom.de":
        from .sources.data_efi_strom import run_import_by_model
        run_import_by_model(model=model, remote_id=remote_id, local_id=local_id)

    if source == "orgamaxx":
        from .sources.orgamaxx import run_import_by_model
        run_import_by_model(model=model, remote_id=remote_id, local_id=local_id)

    if source == "bitrix24":
        from .sources.bitrix24 import run_import_by_model
        run_import_by_model(model=model, remote_id=remote_id, local_id=local_id)

    if source == "daa":
        from .sources.daa import run_import_by_model
        run_import_by_model(model=model, remote_id=remote_id, local_id=local_id)

    if source == "hausfrage":
        from .sources.hausfrage import run_import_by_model
        run_import_by_model(model=model, remote_id=remote_id, local_id=local_id)

    if source == "senec":
        from .sources.senec import run_import_by_model
        run_import_by_model(model=model, remote_id=remote_id, local_id=local_id)

    if source == "wattfox":
        from .sources.wattfox import run_import_by_model
        run_import_by_model(model=model, remote_id=remote_id, local_id=local_id)

    return None


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(ImportIdAssociation, ImportIdAssociationSchema, tree, sort, offset, limit, fields)
