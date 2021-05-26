import datetime
from app import db
from app.modules.settings import get_settings

from ._connector import get, post
from .models.user_cache import UserCache


def get_user(id):
    user_cached = UserCache.query.filter(UserCache.bitrix_id == id).first()
    if user_cached is None or user_cached.last_update is None or user_cached.last_update < (datetime.datetime.now() - datetime.timedelta(days=1)):
        data = post("user.get", {
            "ID": id
        })
        if "result" in data and len(data["result"]) > 0:
            if user_cached is None:
                user_cached = UserCache(bitrix_id=data["result"][0]["ID"])
                db.session.add(user_cached)
            user_cached.email = data["result"][0].get("EMAIL")
            user_cached.department = "".join(str(x) + "," for x in data["result"][0]["UF_DEPARTMENT"])
            user_cached.data = data["result"][0]
            user_cached.last_update = datetime.datetime.now()
            db.session.commit()
            return data["result"][0]
        else:
            print("error get user:", data)
            return None
    return user_cached.data


def get_user_by_email(email):
    user_cached = UserCache.query.filter(UserCache.email == email).first()
    if user_cached is None:
        data = post("user.get", {
            "FILTER[email]": email
        })
        if "result" in data and len(data["result"]) > 0:
            return get_user(data["result"][0]["ID"])
        else:
            print("error get user:", data)
            return None
    return get_user(user_cached.bitrix_id)


def get_users_per_department(department_id):
    refresh = False
    result = []
    users_cached = UserCache.query.filter(UserCache.department.like(f"%{department_id},%")).all()
    for user_cached in users_cached:
        if user_cached.last_update is None or user_cached.last_update < (datetime.datetime.now() - datetime.timedelta(days=1)):
            refresh = True
            break
        result.append(user_cached.data)
    if refresh is True:
        data = post("user.get", {
            "FILTER[UF_DEPARTMENT]": department_id
        })
        if "result" in data and len(data["result"]) > 0:
            for user in data["result"]:
                get_user(user["ID"])
            return data["result"]
        else:
            print("error get user per dep:", data)
            return None
    return result


def cron_refresh_users():
    oldest_user = UserCache.query.order_by(UserCache.last_update.asc()).first()
    if oldest_user.last_update is None or oldest_user.last_update < (datetime.datetime.now() - datetime.timedelta(days=1)):
        print("refreshing users")
        data = post("user.get")
        if "result" in data and len(data["result"]) > 0:
            for user in data["result"]:
                get_user(user["ID"])
    else:
        print("not refreshing users")
        print(oldest_user.last_update)
