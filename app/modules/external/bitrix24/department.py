import json

from app import db
from app.modules.settings import get_settings

from ._connector import get, post
from .models.department import BitrixDepartment

DEPARTMENT_CACHE = {}


def get_department(id):
    department = BitrixDepartment.query.filter(BitrixDepartment.bitrix_id == id).first()
    if department is not None:
        return department.data
    data = post("department.get", {
        "ID": id
    })
    if "result" in data and len(data["result"]) > 0:
        department = BitrixDepartment(bitrix_id=id, data=data["result"][0])
        db.session.add(department)
        db.session.commit()
        return data["result"][0]
    else:
        print("error get department:", data)
    return None
