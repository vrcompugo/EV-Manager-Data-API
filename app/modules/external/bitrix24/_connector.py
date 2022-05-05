import requests
import time
import datetime
import json
import traceback
import sys

from app import db
from app.modules.settings import get_settings
from .models.bitrix24_request_cache import Bitrix24RequestCache


uncacheable_requests = [
    "disk.folder.uploadfile",
    "disk.folder.uploadversion",
    "disk.folder.addsubfolder",
    "crm.lead.update",
    "crm.lead.add",
    "crm.deal.add",
    "crm.deal.update",
    "crm.contact.update",
    "crm.deal.productrows.set",
    "crm.product.list"
]
no_post_store = [
    "disk.folder.uploadfile",
    "disk.folder.uploadversion"
]


def authenticate(domain=None):
    config = get_settings(section="external/bitrix24", domain_raw=domain)
    if config is not None and "url" in config:
        return config["url"]
    return None


def post(url, post_data=None, files=None, domain=None, force_reload=False, recursion=False):
    cached_response = lookup_cache("post", url=url, post_data=post_data, domain=domain, force_reload=force_reload)
    if cached_response is not None:
        return cached_response.response

    base_url = authenticate(domain=domain)

    if base_url is not None:
        response = requests.post(base_url + url, data=post_data)
        try:
            data = response.json()
            if "error" in data and data["error"] == "QUERY_LIMIT_EXCEEDED":
                time.sleep(2)
                return post(url, post_data, files, recursion=True)
            if recursion is False:
                store_cache("post", url=url, post_data=post_data, domain=domain, data=data)
            return data
        except Exception as e:
            print("error", response.text)
    return {}


def get(url, parameters=None, force_reload=False, recursion=False):
    cached_response = lookup_cache("get", url=url, parameters=parameters, force_reload=force_reload)
    if cached_response is not None:
        return cached_response.response

    base_url = authenticate()

    if base_url is not None:
        response = requests.get(base_url + url, params=parameters)
        try:
            data = response.json()
            if "error" in data and data["error"] == "QUERY_LIMIT_EXCEEDED":
                time.sleep(2)
                return get(url, parameters, recursion=True)
            if recursion is False:
                store_cache("get", url=url, parameters=parameters, data=data)
            return data
        except Exception as e:
            print(response.text)
    return {}


def lookup_cache(method, url, parameters=None, post_data=None, domain=None, force_reload=False):
    if url in uncacheable_requests:
        return None
    request_cache = Bitrix24RequestCache.query \
        .filter(Bitrix24RequestCache.method == method) \
        .filter(Bitrix24RequestCache.url == url) \
        .filter(Bitrix24RequestCache.datetime >= datetime.datetime.now() - datetime.timedelta(seconds=600))  # 10min valid cache
    if method == "get":
        request_cache = request_cache.filter(Bitrix24RequestCache.parameters == parameters)
    else:
        request_cache = request_cache.filter(Bitrix24RequestCache.post_data == post_data)
        request_cache = request_cache.filter(Bitrix24RequestCache.domain == domain)
    cached_response = request_cache.first()
    if cached_response is not None:
        if force_reload is True:
            cached_response.fresh_response = cached_response.fresh_response + 1
        else:
            cached_response.cached_responses = cached_response.cached_responses + 1
    db.session.commit()
    if force_reload is True:
        return None
    return cached_response


def store_cache(method, url, parameters=None, post_data=None, domain=None, data=None):
    request_cache = Bitrix24RequestCache()
    request_cache.method = method
    request_cache.url = url
    request_cache.datetime = datetime.datetime.now()
    request_cache.fresh_response = 1
    request_cache.cached_responses = 0
    request_cache.response = data
    if method == "get":
        request_cache.parameters = parameters
    else:
        if url in no_post_store:
            request_cache.post_data = None
        else:
            request_cache.post_data = post_data
        request_cache.domain = domain
    db.session.add(request_cache)
    db.session.commit()
