from app.modules.settings import get_settings

from ._connector import get, post


def get_user(id):
    data = post("user.get", {
        "ID": id
    })
    if "result" in data and len(data["result"]) > 0:
        return data["result"][0]
    else:
        print("error:", data)
    return None
