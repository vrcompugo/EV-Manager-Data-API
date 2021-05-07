import json

from app.modules.external.bitrix24.drive import get_file_content, get_file

from ._connector import get, post


def cli_command():
    session_data = {
        "displayname": "My- First Test-Session",
        "foruser": "a.hedderich@hbb-werbung.de",
        "callbackURL": "https://www.energie360.de/insign/callback/",
        "userFullName": "Max Power",
        "userEmail": "max.power@nowhere.com",
        "documents": [
            {
                "id": 1189230,
                "displayname": "Angebote",
                "signatures": [
                    {
                        "id": "mainsig",
                        "displayname": "Unterschrift",
                        "textsearch": f"__main_sig__",
                        "required": True
                    }
                ]
            },
            {
                "id": 1176366,
                "displayname": "Vertragsunterlagen"
            }
        ]
    }
    sessionId = create_session(session_data)
    print(sessionId)
    for document in session_data["documents"]:
        upload_file(sessionId=sessionId, file_id=document["id"])
    get_public_url(sessionId)


def get_session_id(session_data):
    sessionId = create_session(session_data)
    print("asd", sessionId)
    for document in session_data["documents"]:
        upload_file(sessionId=sessionId, file_id=document["id"])
    return sessionId


def create_session(session_data):
    response = post("/configure/session", post_data=session_data)
    if response is not None and "sessionid" in response:
        return response.get("sessionid")
    else:
        print(response)
    return None


def upload_file(sessionId, file_id):
    file = get_file(file_id)
    if file is None:
        return None
    file["content"] = get_file_content(file_id)

    query_data = {
        "sessionid": sessionId,
        "docid": file_id,
        "filename": file["NAME"]
    }
    files = {
        "file": (file["NAME"], file["content"])
    }
    response = post("/configure/uploaddocument", params=query_data, files=files)
    print(response)


def download_file(sessionId, file_id):
    response = get("/get/document", parameters={
        "sessionid": sessionId,
        "docid": file_id
    }, as_binary=True)
    if response is not None:
        return response
    else:
        print(response)
    return None


def get_public_url(sessionId, recipient):
    post_data = {
        "externUsers": [
            {
                "callbackURL": "https://www.energie360.de/insign-callback/",
                "recipient": recipient,
                "sendEmails": False,
                "singleSignOnEnabled": True
            }
        ]
    }
    response = post("/extern/beginmulti", post_data=post_data, params={
        "sessionid": sessionId
    })
    print(json.dumps(response, indent=2))
    if "externUsers" in response and len(response["externUsers"]) > 0:
        return response["externUsers"][0]["externAccessLink"]
    return None


def send_insign_email(sessionId, recipient):
    post_data = {
        "externUsers": [
            {
                "callbackURL": "https://www.energie360.de/insign-callback/",
                "recipient": recipient,
                "sendEmails": True,
                "singleSignOnEnabled": True
            }
        ]
    }
    response = post("/extern/beginmulti", post_data=post_data, params={
        "sessionid": sessionId
    })
    print(recipient)
    print(response)
    if "externUsers" in response and len(response["externUsers"]) > 0:
        return {
            "is_sent": True,
            "email": recipient
        }
    return {
        "is_sent": False,
        "email": recipient
    }
