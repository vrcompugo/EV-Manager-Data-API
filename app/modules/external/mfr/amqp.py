from datetime import datetime
from app import db
from azure.servicebus import ServiceBusClient, ServiceBusReceivedMessage
from app.models import MfrLogEvent
from app.utils.error_handler import error_handler
from .task import import_by_id


def run_mfr_amqp_messaging_subscriptor():
    connstr = f"Endpoint=sb://mfr-prod.servicebus.windows.net/;SharedAccessKeyName=listenRule;SharedAccessKey=9dWzdLFU5cKzTHCfE4xsqCGE2AhjheIRjLtqXJgS7kY="
    queue_name = "kez-bitrix"
    with ServiceBusClient.from_connection_string(connstr) as client:
        # max_wait_time specifies how long the receiver should wait with no incoming messages before stopping receipt.
        # Default is None; to receive forever.
        with client.get_subscription_receiver(topic_name="17291739136", subscription_name=queue_name) as receiver:
            for msg in receiver:
                print("asd", msg.__dict__)
                if msg.message._application_properties.get(b"ServiceRequestId", None) is not None:
                    service_request_id = str(msg.message._application_properties.get(b"ServiceRequestId", None))
                    if service_request_id not in ["", "0"]:
                        try:
                            print(service_request_id)
                            store_log_event(service_request_id)
                        except Exception as e:
                            error_handler()


def store_log_event(service_request_id):
    event = MfrLogEvent(service_request_id=service_request_id, last_change=datetime.now(), processed=False)
    db.session.add(event)
    db.session.commit()


def run_cron_import():
    events = MfrLogEvent.query.filter(MfrLogEvent.processed.is_(False)).all()
    for event in events:
        try:
            import_by_id(event.service_request_id)
            event.processed = True
            db.session.commit()
        except Exception as e:
            error_handler()