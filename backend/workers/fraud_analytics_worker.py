import json
import time
from kafka import KafkaConsumer

import os

# --- Configuration ---
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')
TOPIC = 'payment.completed'

def start_worker():
    print("Starting Fraud Analytics Worker...")
    
    consumer = None
    while not consumer:
        try:
            consumer = KafkaConsumer(
                TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='earliest',
                group_id='fraud_analytics_group'
            )
            print("Connected to Kafka!")
        except Exception as e:
            print(f"Waiting for Kafka... {e}")
            time.sleep(5)

    for message in consumer:
        transaction = message.value
        # In a real system, we would update a user's fraud profile here
        # For now, we just log it
        print(f"[FRAUD ANALYTICS] Analyzing transaction {transaction['transaction_id']} for user {transaction['sender_id']}")
        
        # Simulate ML model training update
        if transaction['amount'] > 5000:
             print(f"[FRAUD ANALYTICS] High value transaction detected. Updating risk profile.")

if __name__ == "__main__":
    start_worker()
