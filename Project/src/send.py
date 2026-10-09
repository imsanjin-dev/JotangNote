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

with pika.BlockingConnection(parameters) as connection:
    channel = connection.channel()
    channel.queue_declare(queue="hello", durable=True)
    channel.basic_publish(
        exchange="",
        routing_key="hello",
        body="Hello RabbitMQ!"
    )
    print("Message sent!")