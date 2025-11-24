import json
import time
from kafka import KafkaConsumer

import os

# --- Configuration ---
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')
TOPIC = 'payment.completed'

def start_worker():
    print("Starting Notification Worker...")
    
    # Retry connection logic
    consumer = None
    while not consumer:
        try:
            consumer = KafkaConsumer(
                TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='earliest',
                group_id='notification_group'
            )
            print("Connected to Kafka!")
        except Exception as e:
            print(f"Waiting for Kafka... {e}")
            time.sleep(5)

    for message in consumer:
        transaction = message.value
        print(f"[NOTIFICATION] Sending SMS to {transaction['sender_id']}: Payment of {transaction['amount']} successful!")
        print(f"[NOTIFICATION] Sending SMS to {transaction['receiver_id']}: You received {transaction['amount']}!")

if __name__ == "__main__":
    start_worker()
