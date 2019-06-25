

def set_attr_by_dict(item, data, blacklist=None, fields=None):
    if fields is None:
        fields = data.keys()
    for field in fields:
        if field in data and hasattr(item, field) and (blacklist is None or field not in blacklist):
            setattr(item, field, data[field])
    return item
