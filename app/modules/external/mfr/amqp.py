import json
from azure.servicebus import ServiceBusClient, ServiceBusReceivedMessage
from .task import import_by_id


def run_mfr_amqp_messaging_subscriptor():
    connstr = f"Endpoint=sb://mfr-prod.servicebus.windows.net/;SharedAccessKeyName=listenRule;SharedAccessKey=9dWzdLFU5cKzTHCfE4xsqCGE2AhjheIRjLtqXJgS7kY="
    queue_name = "kez-bitrix"
    with ServiceBusClient.from_connection_string(connstr) as client:
        # max_wait_time specifies how long the receiver should wait with no incoming messages before stopping receipt.
        # Default is None; to receive forever.
        with client.get_subscription_receiver(topic_name="17291739136", subscription_name=queue_name) as receiver:
            for msg in receiver:
                if msg.message._application_properties.get(b"ServiceRequestId", None) is not None:
                    service_request_id = str(msg.message._application_properties.get(b"ServiceRequestId", None))
                    if service_request_id not in ["", "0"]:
                        import_by_id(service_request_id)