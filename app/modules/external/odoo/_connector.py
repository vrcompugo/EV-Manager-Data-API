import requests

from app.modules.settings import get_settings


def patch(url, post_data=None):
    config = get_settings("external/odoo")

    if config['header_key'] is not None:
        base_url = config["url"]
        response = requests.patch(
            base_url + url,
            auth=(config['username'], config['password']),
            headers={
                "Accept": "*/*",
                config['header_key']: config['header_value']
            },
            json=post_data
        )
        try:
            data = response.json()
            return data
        except Exception as e:
            print("odoo error:", response.request.method, response.request.url, response.request.headers, response.request.body, response.text)
    return None