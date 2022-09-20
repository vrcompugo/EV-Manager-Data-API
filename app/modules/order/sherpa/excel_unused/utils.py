

def get_data_value(path, data):
    for node in path:
        if type(node) == "int":
            if len(data) > node:
                data = data[node]
        else:
            if node in data:
                data = data[node]
            else:
                return ""
    if data is None:
        return ""
    return data
