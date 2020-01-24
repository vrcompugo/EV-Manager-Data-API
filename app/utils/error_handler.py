import traceback
from flask_emails import Message

from app.config import email_config


def error_handler():
    print("error-handling")
    trace_output = traceback.format_exc()
    print(trace_output)
    message = Message(text=trace_output,
                      subject="Error EV-Manager-API",
                      mail_from=("EV-Manager", "bugs@api.korbacher-energiezentrum.de"),
                      config=email_config)

    message.mail_to = "a.hedderich@hbb-werbung.de"
    message.send()
