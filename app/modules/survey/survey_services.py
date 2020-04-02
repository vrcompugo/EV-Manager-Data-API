import datetime

from app import db
from app.exceptions import ApiException
from app.utils.get_items_by_model import get_items_by_model, get_one_item_by_model
from app.utils.set_attr_by_dict import set_attr_by_dict
from app.modules.offer.offer_services import automatic_offer_creation_by_survey

from .models.survey import Survey, SurveySchema, DATA_STATUSES, OFFER_STATUSES


def add_item(data):
    from app.modules.importer.sources.bitrix24.survey import run_export as bitrix24_export

    new_item = Survey()
    new_item = set_attr_by_dict(new_item, data, ["id"])
    db.session.add(new_item)
    db.session.commit()
    automatic_offer_creation_by_survey(new_item)
    try:
        bitrix24_export(local_id=new_item.id)
    except Exception as e:
        print(e)
    return new_item


def update_item(id, data):
    from app.modules.importer.sources.bitrix24.survey import run_export as bitrix24_export

    item = db.session.query(Survey).get(id)
    if item is not None:
        item_schema = SurveySchema()
        old_data = item_schema.dump(item, many=False)
        updated_item = set_attr_by_dict(item, data, ["id"])
        db.session.commit()
        try:
            automatic_offer_creation_by_survey(survey=updated_item, old_data=old_data)
        except Exception as e:
            print(e)
        try:
            bitrix24_export(local_id=item.id)
            pass
        except Exception as e:
            print(e)
        return item
    else:
        raise ApiException("item_doesnt_exist", "Item doesn't exist.", 409)


def get_items(tree, sort, offset, limit, fields):
    return get_items_by_model(Survey, SurveySchema, tree, sort, offset, limit, fields)


def get_one_item(id, fields=None):
    return get_one_item_by_model(Survey, SurveySchema, id, fields)
