from functools import wraps
from app.exceptions import ApiException


def api_response(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        try:
            print(f(*args, **kwargs))
            return f(*args, **kwargs)
        except ApiException as e:
            print(e)
            return {"status": "error", "code": e.code, "messsage": e.message}, e.http_status
        except Exception as e:
            print(str(e))
            return {"status": "error", "code": "unkown", "messsage": "Unknown Error"}, 500

    return decorated
