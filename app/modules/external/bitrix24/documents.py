import json

from app.modules.settings import get_settings

from ._connector import post, get


def get_documents(payload):
    payload["start"] = 0
    result = []
    while payload["start"] is not None:
        print(payload)
        data = post("crm.documentgenerator.document.list", payload, force_reload=True)
        if "result" in data:
            payload["start"] = data["next"] if "next" in data else None
            for item in data["result"]["documents"]:
                result.append(item)
        else:
            print("error3:", data)
            payload["start"] = None
            return None
    return result
