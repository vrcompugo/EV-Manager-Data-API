import traceback
from flask_emails import Message

from app.config import email_config


def error_handler():
    trace_output = traceback.format_exc()
    print(traceback)
    message = Message(text=message,
                      subject="Error EV-Manager-API:" + message,
                      mail_from=("EV-Manager", "bugs@api.korbacher-energiezentrum.de"),
                      config=email_config)

    message.mail_to = "a.hedderich@hbb-werbung.de"
    message.send()
