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
    if "result" in data and len(data["result"]) > 0:
        DEPARTMENT_CACHE[id] = data["result"][0]
        return DEPARTMENT_CACHE[id]
    else:
        print("error:", data)
    return None
