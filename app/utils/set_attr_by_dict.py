

def set_attr_by_dict(item, data, blacklist=None, fields=None, merge=False):
    if fields is None:
        fields = data.keys()
    for field in fields:
        if field in data and hasattr(item, field) and (blacklist is None or field not in blacklist):
            if str(field) == "_sa_instance_state":
                continue
            if merge:
                if str(data[field]) != "" and str(data[field]) != "0":
                    setattr(item, field, data[field])
            else:
                setattr(item, field, data[field])
    return item
