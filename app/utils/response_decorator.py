import sys
import traceback
import json
from functools import wraps
from flask import Response

from app.exceptions import ApiException


def api_response(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        try:
            return f(*args, **kwargs)
        except ApiException as e:
            print(e)
            traceback.print_exc(file=sys.stdout)
            return {"status": "error", "code": e.code, "message": e.message}, e.http_status
        except Exception as e:
            message = ""
            if hasattr(e, 'message'):
                message = e.message
            else:
                message = f"{type(e).__name__}: {e}"
            traceback.print_exc(file=sys.stdout)
            return Response(
                json.dumps({"status": "error", "error_code": "exception", "message": message}),
                status=500,
                mimetype='application/json')

    return decorated
