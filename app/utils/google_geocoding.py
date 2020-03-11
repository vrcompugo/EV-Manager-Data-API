import requests

from app.modules.settings.settings_services import get_one_item

config = get_one_item("google/api")


def geocode_address(address):
    if config is None or "data" not in config or "key" not in config["data"]:
        return None
    location = None

    r = requests.get(
        f'https://maps.googleapis.com/maps/api/geocode/json?key=' + config["data"]["key"],
        params={
            'sensor': 'false',
            'address': address
        })
    results = r.json()
    if 'results' in results and len(results['results']) > 0:
        location = results['results'][0]['geometry']['location']
    return location


def route_to_address(address):
    if config is None or "data" not in config or "key" not in config["data"]:
        return None
    route = None

    r = requests.get(
        f'https://maps.googleapis.com/maps/api/directions/json?key=' + config["data"]["key"],
        params={
            'origin': config["data"]["home_address"],
            'destination': address
        })
    results = r.json()
    if 'routes' in results and len(results["routes"]) > 0:
        route = {"distance": 0, "duration": 0}
        for leg in results["routes"][0]["legs"]:
            route["distance"] = round(leg["distance"]["value"] / 1000)
            route["duration"] = round(leg["duration"]["value"] / 60)
    return route
