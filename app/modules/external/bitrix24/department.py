import json

from app.modules.settings import get_settings

from ._connector import get, post

DEPARTMENT_CACHE = {}


def get_department(id):
    if id in DEPARTMENT_CACHE:
        return DEPARTMENT_CACHE[id]
    data = post("department.get", {
        "ID": id
    })
    if "result" in data:
        DEPARTMENT_CACHE[id] = data["result"]
        return DEPARTMENT_CACHE[id]
    else:
        print("error:", data)
    return None
