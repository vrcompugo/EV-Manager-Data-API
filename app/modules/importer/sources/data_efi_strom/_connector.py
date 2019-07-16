import requests
import json
import base64


def authenticate():
    response = requests.get("https://data.efi-strom.de/AuthToken",
                            auth=('ahedderich', 'iYfXea3Vg1VuGzyJDl3FaBUiR5psJsAw'))

    if response.status_code == 200:

        data = json.loads(response.text)
        if "token" in data:
            token = data["token"] + ":"
            return str(base64.b64encode(bytes(token, encoding="utf8"))).strip("b'")
    return None


def post(url, post_data = None):

    token = authenticate()

    if token is not None:
        response = requests.post("https://data.efi-strom.de/v1/{}".format(url),
                                     headers={'Authorization': "Basic {}".format(token)},
                                     json=post_data)
        try:
            return response.json()
        except:
            print(response.text)
    return {}
