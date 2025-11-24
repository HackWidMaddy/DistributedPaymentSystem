import json
import time
import requests
from kafka import KafkaConsumer

import os

# --- Configuration ---
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')
TOPIC = 'payment.completed'
MERCHANT_SERVICE_URL = os.getenv("MERCHANT_SERVICE_URL", "http://localhost:6200")

def start_worker():
    print("Starting Settlement Worker...")
    
    consumer = None
    while not consumer:
        try:
            consumer = KafkaConsumer(
                TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                auto_offset_reset='earliest',
                group_id='settlement_group'
            )
            print("Connected to Kafka!")
        except Exception as e:
            print(f"Waiting for Kafka... {e}")
            time.sleep(5)

    for message in consumer:
        transaction = message.value
        receiver_id = transaction['receiver_id']
        amount = transaction['amount']
        
        # Check if receiver is a merchant (simple check: starts with 'MERCHANT')
        if receiver_id.startswith('MERCHANT'):
            print(f"[SETTLEMENT] Processing settlement for {receiver_id} amount {amount}")
            
            # Trigger payout (in real world, this might be batched)
            try:
                requests.post(f"{MERCHANT_SERVICE_URL}/merchant/payout", json={
                    "merchant_id": receiver_id,
                    "amount": amount
                })
            except Exception as e:
                print(f"[SETTLEMENT] Error triggering payout: {e}")

if __name__ == "__main__":
    start_worker()
