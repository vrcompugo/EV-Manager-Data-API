from functools import wraps
import sys, traceback

from app.exceptions import ApiException


def api_response(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        try:
            return f(*args, **kwargs)
        except ApiException as e:
            print(e)
            return {"status": "error", "code": e.code, "message": e.message}, e.http_status
        except Exception as e:
            print(str(e))
            traceback.print_exc(file=sys.stdout)
            return {"status": "error", "code": "unkown", "message": "Unknown Error"}, 500

    return decorated
