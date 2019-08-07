import requests

API_URL = "https://2ei3scwibnc5bkfm.myfritz.net:5000/v1/"


def authenticate():
    response = requests.post(
        API_URL + "login",
        json={
            "USER": "ahedderich",
            "PASSWORD": "R834IutVlxBSuUBIRO2b"
        },
        verify=False
    )
    if response.status_code == 200:
        data = response.json()
        if "Authorization" in data:
            return data["Authorization"]

    return None


def post(url, post_data = None):

    token = authenticate()

    if token is not None:
        response = requests.post(API_URL + url,
                                 headers={'Authorization': token},
                                 json=post_data,
                                 verify=False)
        try:
            return response.json()
        except:
            print(response.text)
    return {}


def get(url, parameters=None):

    token = authenticate()

    if token is not None:
        response = requests.get(API_URL + format(url),
                                 params=parameters,
                                 headers={'Authorization': token},
                                 verify=False)
        try:
            return response.json()
        except:
            print(response.text)
    return {}
