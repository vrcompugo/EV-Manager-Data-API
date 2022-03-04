from app import db
from decimal import Decimal
from sqlalchemy.inspection import inspect


def _extract_sublist(list, key):
    if list is None:
        return None
    sublist = []
    for item in list:
        if item.startswith(key + "."):
            sublist.append(item[len(key) + 1:])
    if len(sublist) > 0:
        return sublist
    return None


def get_dict_attr(item, key):
    value = getattr(item, key)
    if value is None or isinstance(value, list) or isinstance(value, dict) or isinstance(value, bool) or isinstance(value, db.Model):
        return value
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def to_dict(item, whitelist=None, blacklist=None):
    data = {}
    for c in inspect(item).mapper.column_attrs:
        if blacklist is not None:
            if c.key not in blacklist:
                data[c.key] = get_dict_attr(item, c.key)
        else:
            if whitelist is not None:
                if c.key in whitelist:
                    data[c.key] = get_dict_attr(item, c.key)
            else:
                data[c.key] = get_dict_attr(item, c.key)

    for relationship in inspect(item).mapper.relationships:
        if relationship.key in item.__dict__ and (blacklist is None or relationship.key not in blacklist):
            sub_whitelist = _extract_sublist(item, whitelist, relationship.key)
            sub_blacklist = _extract_sublist(item, blacklist, relationship.key)
            value = getattr(item, relationship.key)
            if value is not None:
                if isinstance(value, list):
                    data[relationship.key] = []
                    for item in value:
                        data[relationship.key].append(
                            to_dict(item, whitelist=sub_whitelist, blacklist=sub_blacklist))
                else:
                    data[relationship.key] = value.to_dict()
            else:
                data[relationship.key] = None

    return data
