import requests

from app.models import Reseller


def get_bitrix_auth_info(request):
    data = {
        "auth_code": request.form.get("AUTH_ID") if request.form.get("AUTH_ID") else request.args.get("AUTH_ID"),
        "domain": "https://{}".format(request.args.get("DOMAIN")),
        "domain_raw": request.args.get("DOMAIN"),
        "bitrix_user": None,
        "user": None
    }

    if data["domain"] != "https://None":
        x = requests.post(data["domain"] + "/rest/user.current.json",
                          data={
                              "auth": data["auth_code"]
                          })
        response_data = x.json()
        if "result" in response_data:
            data["bitrix_user"] = {}
            for k,v in response_data["result"].items():
                data["bitrix_user"][k.lower()] = v
        if data["bitrix_user"] is not None and "email" in data["bitrix_user"]:
            reseller = Reseller.query.filter(Reseller.email == data["bitrix_user"]["email"]).first()
            if reseller is not None:
                data["user"] = reseller
    return data
