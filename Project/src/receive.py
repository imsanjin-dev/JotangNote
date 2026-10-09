import os
import pika

credentials = pika.PlainCredentials(
    "jotang",
    os.environ["RABBITMQ_PASSWORD"]
)

parameters = pika.ConnectionParameters(
    host="127.0.0.1",
    port=5672,
    credentials=credentials
)

def callback(ch, method, properties, body):
    print("Received:", body.decode("utf-8"))
    ch.basic_ack(delivery_tag=method.delivery_tag)
    print("ACK sent!")

with pika.BlockingConnection(parameters) as connection:
    channel = connection.channel()
    channel.queue_declare(queue="hello", durable=True)

    channel.basic_consume(
        queue="hello",
        on_message_callback=callback,
        auto_ack=False
    )

    print("Waiting for messages...")
    channel.start_consuming()