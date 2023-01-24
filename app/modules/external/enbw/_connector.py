import requests
import datetime
import base64
import random
import hmac
import hashlib
import re

from app import db
from app.modules.settings import get_settings
from .models.enbw_contract import ENBWContract
from .models.enbw_contract_history import ENBWContractHistory


def get(url, parameters=None, contract:ENBWContract=None):
    config = get_settings("external/enbw")

    token = config['api_key']

    if token is not None:
        history = None
        if contract is not None:
            history = ENBWContractHistory(
                enbw_contract_id=contract.id,
                action=url,
                datetime=datetime.datetime.now(),
                post_data=parameters
            )
            db.session.add(history)
        response = requests.get(
            config["url"] + url,
            headers={
                "Accept": "application/json",
                "Api-KEY": token
            },
            params=parameters
        )
        if history is not None:
            history.api_response_status = response.status_code
        try:
            data = response.json()
            if history is not None:
                history.api_response = data
                db.session.commit()
            return data
        except Exception as e:
            if history is not None:
                history.api_response_raw = response.text
                db.session.commit()
            print(response.text)
    return None


def post(url, post_data=None, files=None, contract:ENBWContract=None):
    config = get_settings("external/enbw")

    token = config['api_key']

    if token is not None:
        history = None
        if contract is not None:
            history = ENBWContractHistory(
                enbw_contract_id=contract.id,
                action=url,
                datetime=datetime.datetime.now(),
                post_data=post_data
            )
            db.session.add(history)
        base_url = config["url"]
        if url == "/tariffs":
            base_url = "https://enbw-staging.joulesapp.de/service"
        response = requests.post(
            base_url + url,
            headers={
                "Accept": "application/json",
                "Api-KEY": token
            },
            json=post_data
        )
        if history is not None:
            history.api_response_status = response.status_code
        try:
            data = response.json()
            if history is not None:
                history.api_response = data
                db.session.commit()
            return data
        except Exception as e:
            if history is not None:
                history.api_response_raw = response.text
                db.session.commit()
            print(response.text)
    return None


def put(url, post_data=None, files=None, contract:ENBWContract=None):
    config = get_settings("external/enbw")

    token = config['api_key']

    if token is not None:
        history = None
        if contract is not None:
            history = ENBWContractHistory(
                enbw_contract_id=contract.id,
                action=url,
                datetime=datetime.datetime.now(),
                post_data=post_data
            )
            db.session.add(history)
        response = requests.put(
            config["url"] + url,
            headers={
                "Accept": "application/json",
                "Api-KEY": token
            },
            json=post_data
        )
        if history is not None:
            history.api_response_status = response.status_code
        try:
            data = response.json()
            if history is not None:
                history.api_response = data
                db.session.commit()
            return data
        except Exception as e:
            if history is not None:
                history.api_response_raw = response.text
                db.session.commit()
            print(response.text)
    return None