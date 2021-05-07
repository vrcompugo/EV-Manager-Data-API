import jwt
import datetime
from app.config import key


def encode_jwt(data, expire_minutes=100):
    data["exp"] = datetime.datetime.utcnow() + datetime.timedelta(minutes=expire_minutes)
    data["iat"] = datetime.datetime.utcnow()

    token = jwt.encode(
        data,
        key,
        algorithm='HS256')
    data["token"] = token.decode("utf-8")
    return data


def decode_jwt(token):
    return jwt.decode(token, key)


def encode_shared_jwt(data, expire_minutes=100, shared_key="UrRP2T9FCDzVp04mHfPzfgzDhB2ElKTk"):
    data["exp"] = datetime.datetime.utcnow() + datetime.timedelta(minutes=expire_minutes)
    data["iat"] = datetime.datetime.utcnow()

    token = jwt.encode(
        data,
        shared_key,
        algorithm='HS256')
    data["token"] = token.decode("utf-8")
    return data