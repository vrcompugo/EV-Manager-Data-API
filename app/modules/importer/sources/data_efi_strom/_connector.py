import requests
import json
import base64


def post(url, post_data = None):

    response = requests.get("https://data.efi-strom.de/AuthToken",
                            auth=('ahedderich', 'iYfXea3Vg1VuGzyJDl3FaBUiR5psJsAw'))

    if response.status_code == 200:

        data = json.loads(response.text)
        if "token" in data:
            token = data["token"] + ":"
            b64Val = str(base64.b64encode(bytes(token, encoding="utf8"))).strip("b'")
            response = requests.post("https://data.efi-strom.de/v1/{}".format(url),
                                     headers={'Authorization': "Basic {}".format(b64Val)},
                                     json=post_data)
            return response.json()
