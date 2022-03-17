import sys
import traceback
import json
import datetime
from functools import wraps
from flask import Response, request

from app import db
from app.exceptions import ApiException
from app.models import RequestLog


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


def log_request(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        start_time = datetime.datetime.now()
        response = f(*args, **kwargs)
        request_log = RequestLog()
        request_log.route = str(request.url_rule)[:254]
        request_log.datetime = start_time
        request_log.url = str(request.url)[:254]
        request_log.post_data = request.form
        request_log.json = request.json
        request_log.method = request.method
        request_log.duration_milliseconds = int((datetime.datetime.now() - request_log.datetime).total_seconds() * 1000)
        db.session.add(request_log)
        db.session.commit()
        return response

    return decorated
