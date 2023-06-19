import requests
import datetime
import base64
import random
import hmac
import hashlib
import re
import pysftp
import os

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


def get_ftp_connection():
    cnopts = pysftp.CnOpts(knownhosts='known_hosts')
    host = 'energyretail.de'
    port = 22
    username = 'energie360_enbw'
    password= 'rvsgda7Wrn6w9YYbP15I'
    try:
        conn = pysftp.Connection(host=host,port=port,username=username, password=password, cnopts=cnopts)
        print("connection established successfully")
    except:
        print('failed to establish connection to targeted server')
    return conn


def get_ftp_file(path):
    conn = get_ftp_connection()
    filename = get_temp_file_name()
    try:
        conn.get(path, filename)
        with open(filename, 'r', encoding='utf-8', errors='ignore') as fh:
            content = fh.read()
    except Exception as e:
        print(e)
        return None
    os.unlink(filename)
    return content


def rename_ftp_file(path, new_path):
    conn = get_ftp_connection()
    return conn.rename(path, new_path)


def get_temp_file_name():
    return f"tmp_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(0, 1000000)}"