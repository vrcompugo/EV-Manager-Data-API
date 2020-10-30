
def flatten_dict(data, post_data, fields, path="fields", config=None, dict_key=None):
    if type(data) is list:
        for key in range(len(data)):
            new_path = f"{path}[{key}]"
            post_data = flatten_dict(data[key], post_data, fields, path=new_path, config=config, dict_key=dict_key)
        return post_data

    if type(data) is dict:
        for key in data.keys():
            new_path = f"{path}[{key.upper()}]"
            if key in fields:
                new_path = f"{path}[{fields[key]}]"
            post_data = flatten_dict(data[key], post_data, fields, path=new_path, config=config, dict_key=key)
        return post_data

    if type(data) is bool:
        post_data[path] = "0"
        if data:
            post_data[path] = "1"
        return post_data

    if config is not None and dict_key is not None and dict_key in config["select_lists"]:
        for k, v in config["select_lists"][dict_key].items():
            if str(data) == str(v):
                data = k

    post_data[path] = data
    return post_data
