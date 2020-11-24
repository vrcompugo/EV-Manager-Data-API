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


def get_users_per_department(department_id):
    data = post("user.get", {
        "FILTER[UF_DEPARTMENT]": department_id
    })
    if "result" in data and len(data["result"]) > 0:
        return data["result"]
    else:
        print("error:", data)
    return None
