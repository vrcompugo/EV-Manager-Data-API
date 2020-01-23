import requests

from app.modules.settings.settings_services import get_one_item

config = get_one_item("google/api")


def geocode_address(address):
    if config is None or "data" not in config or "key" not in config["data"]:
        return None
    location = None

    r = requests.get(f'https://maps.googleapis.com/maps/api/geocode/json?key=' + config["data"]["key"],
                     params={
                         'sensor': 'false',
                         'address': address
                     })
    results = r.json()
    print(results)
    if 'results' in results and len(results['results']) > 0:
        location = results['results'][0]['geometry']['location']
    return location
