import sys
import argparse
import threading
import time
import requests
import json
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from kafka import KafkaProducer
from logging_client import LoggingClient

app = Flask(__name__)
CORS(app)
logger = None

import os

# --- Configuration ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:28000/")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(',')
FRAUD_SERVICE_URL = os.getenv("FRAUD_SERVICE_URL", "http://localhost:7100")
WALLET_SERVICE_URL = os.getenv("WALLET_SERVICE_URL", "http://localhost:6100")

# --- Global State ---
ROLE = "primary" # or "backup"
PEER_URL = "http://localhost:6001"
PORT = 6000
IS_ACTIVE = True # For simulating failure
LAG_MS = 0 # For simulating network lag

# --- Database Setup ---
client = MongoClient(MONGO_URI)
db = client.payflow
transactions_col = db.transactions

# --- Kafka Producer ---
producer = None
def get_producer():
    global producer
    if producer is None:
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
        except Exception as e:
            print(f"Error connecting to Kafka: {e}")
    return producer

# --- Heartbeat & Failover Logic ---
last_heartbeat = time.time()

def heartbeat_loop():
    global last_heartbeat, ROLE
    while True:
        if ROLE == "backup":
            # Check if primary is alive
            if time.time() - last_heartbeat > 5:
                print("Primary is dead! Promoting to Primary...")
                ROLE = "primary"
                # In a real system, we would update a service registry or DNS
        else:
            # Send heartbeat to backup
            if IS_ACTIVE:
                try:
                    requests.post(f"{PEER_URL}/heartbeat", timeout=1)
                except:
                    pass # Backup might be down, that's fine
        time.sleep(2)

threading.Thread(target=heartbeat_loop, daemon=True).start()

# --- Core Transaction Logic ---

def process_payment(data):
    transaction_id = data['transaction_id']
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    amount = float(data['amount'])
    
    if not IS_ACTIVE:
        return {"error": "Coordinator is down"}, 503
        
    if LAG_MS > 0:
        time.sleep(LAG_MS / 1000.0)
    
    if logger: logger.log(f"Processing transaction {transaction_id}")
    
    # 1. Check Fraud
    try:
        fraud_resp = requests.post(f"{FRAUD_SERVICE_URL}/check", json={"user_id": sender_id, "amount": amount}, timeout=2)
        if fraud_resp.status_code == 200 and fraud_resp.json().get('fraud_score', 0) > 0.8:
            return {"status": "BLOCKED", "reason": "fraud"}
    except:
        print("Fraud service unavailable, proceeding with caution")

    # 2. Debit Sender (Prepare Phase)
    # We need to lock funds. For simplicity, we'll call wallet service to debit.
    # If it fails, we abort.
    try:
        debit_resp = requests.post(f"{WALLET_SERVICE_URL}/wallet/debit", json={
            "user_id": sender_id, 
            "amount": amount, 
            "transaction_id": transaction_id
        }, timeout=5)
        
        if debit_resp.status_code != 200:
            return {"status": "FAILED", "reason": "insufficient_balance"}
    except:
        return {"status": "FAILED", "reason": "wallet_service_error"}
        
    # 3. Replicate to Backup
    if ROLE == "primary":
        try:
            requests.post(f"{PEER_URL}/replicate", json=data, timeout=2)
        except:
            print("Backup replication failed")

    # 4. Credit Receiver (Commit Phase)
    try:
        requests.post(f"{WALLET_SERVICE_URL}/wallet/credit", json={
            "user_id": receiver_id, 
            "amount": amount, 
            "transaction_id": transaction_id
        }, timeout=5)
    except:
        # This is bad. Sender debited, receiver not credited.
        # In real 2PC, we would have a recovery mechanism.
        # Here we'll log it and maybe a background worker fixes it.
        print("CRITICAL: Credit failed after debit!")
        return {"status": "PARTIAL_FAILURE", "reason": "credit_failed"}

    # 5. Publish to Kafka
    prod = get_producer()
    if prod:
        prod.send('payment.completed', data)
        prod.flush()

    # 6. Save to DB
    data['status'] = 'COMPLETED'
    transactions_col.insert_one(data)
    
    return {"status": "SUCCESS", "transaction_id": transaction_id}

# --- Endpoints ---

@app.route('/health', methods=['GET'])
def health():
    if not IS_ACTIVE:
        return jsonify({"status": "OFFLINE", "role": ROLE}), 503
    return jsonify({"status": "ONLINE", "role": ROLE, "lag_ms": LAG_MS})

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    global last_heartbeat
    last_heartbeat = time.time()
    return "OK", 200

@app.route('/transaction/initiate', methods=['POST'])
def initiate_transaction():
    if ROLE != "primary":
        return jsonify({"error": "Not Primary"}), 503
        
    data = request.json
    result = process_payment(data)
    return jsonify(result)

@app.route('/replicate', methods=['POST'])
def replicate():
    # Save state from primary
    data = request.json
    transactions_col.insert_one(data)
    return "OK", 200

@app.route('/transaction/status/<transaction_id>', methods=['GET'])
def get_status(transaction_id):
    txn = transactions_col.find_one({"transaction_id": transaction_id}, {"_id": 0})
    if txn:
        return jsonify(txn)
    return jsonify({"error": "Transaction not found"}), 404

@app.route('/simulate/kill', methods=['POST'])
def simulate_kill():
    global IS_ACTIVE
    IS_ACTIVE = False
    return jsonify({"status": "KILLED", "message": "Coordinator is now simulating failure"})

@app.route('/simulate/lag', methods=['POST'])
def simulate_lag():
    global LAG_MS
    LAG_MS = 2000 # 2 seconds lag
    return jsonify({"status": "LAGGING", "message": "Network lag of 2s simulated"})

@app.route('/simulate/reset', methods=['POST'])
def simulate_reset():
    global IS_ACTIVE, LAG_MS
    IS_ACTIVE = True
    LAG_MS = 0
    return jsonify({"status": "RESET", "message": "System restored to normal"})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", type=str, default="primary", help="Role: primary or backup")
    parser.add_argument("--port", type=int, default=6000, help="Port to run on")
    parser.add_argument("--peer", type=str, default="http://localhost:6001", help="Peer URL")
    
    args = parser.parse_args()
    
    ROLE = args.role
    PORT = args.port
    PEER_URL = args.peer
    logger = LoggingClient(f"Coordinator-{ROLE}")
    
    print(f"Starting Transaction Coordinator ({ROLE}) on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
