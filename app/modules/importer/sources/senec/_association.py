from app import db
from app.modules.importer.models.import_id_association import ImportIdAssociation


def find_association(model, remote_id=None, local_id=None):
    if remote_id is None and local_id is None:
        return None
    query = db.session.query(ImportIdAssociation)\
        .filter(ImportIdAssociation.source == "senec")\
        .filter(ImportIdAssociation.model == model)
    if remote_id is not None:
        query = query.filter(ImportIdAssociation.remote_id == remote_id)
    if local_id is not None:
        query = query.filter(ImportIdAssociation.local_id == local_id)
    return query.first()


def associate_item(model, remote_id, local_id):
    item = find_association(model, remote_id, local_id)
    if item is None:
        item = ImportIdAssociation(
            source="senec",
            model=model,
            local_id=local_id,
            remote_id=remote_id
        )
        db.session.add(item)
        db.session.commit()
