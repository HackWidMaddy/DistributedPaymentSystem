import sys
import argparse
import threading
import time
import requests
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from logging_client import LoggingClient

app = Flask(__name__)
CORS(app)
logger = None # Will be initialized in main

import os

# --- Configuration ---
COORDINATOR_URL = os.getenv("COORDINATOR_URL", "http://localhost:6000") # Primary
BACKUP_COORDINATOR_URL = os.getenv("BACKUP_COORDINATOR_URL", "http://localhost:6001")
WALLET_SERVICE_URL = os.getenv("WALLET_SERVICE_URL", "http://localhost:6100")

# --- Global State ---
SERVER_NAME = "PaymentAPI"
PORT = 5000

# --- Helper Functions ---

def get_coordinator_url():
    # Simple failover logic: try primary, if fails, try backup
    try:
        resp = requests.get(f"{COORDINATOR_URL}/health", timeout=0.5)
        if resp.status_code == 200:
            return COORDINATOR_URL
        return BACKUP_COORDINATOR_URL
    except:
        return BACKUP_COORDINATOR_URL

# --- Endpoints ---

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ONLINE", "server": SERVER_NAME})

@app.route('/api/payment/initiate', methods=['POST'])
def initiate_payment():
    data = request.json
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')
    amount = data.get('amount')
    
    if not sender_id or not receiver_id or amount is None:
        return jsonify({"error": "Missing required fields"}), 400
        
    transaction_id = str(uuid.uuid4())
    logger.log(f"Initiating payment {transaction_id} from {sender_id} to {receiver_id}")
    
    # Forward to Transaction Coordinator
    coordinator = get_coordinator_url()
    payload = {
        "transaction_id": transaction_id,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "amount": amount,
        "timestamp": time.time()
    }
    
    try:
        response = requests.post(f"{coordinator}/transaction/initiate", json=payload, timeout=5)
        return (response.content, response.status_code, response.headers.items())
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Transaction Coordinator unreachable"}), 503

@app.route('/api/payment/status/<transaction_id>', methods=['GET'])
def payment_status(transaction_id):
    coordinator = get_coordinator_url()
    try:
        response = requests.get(f"{coordinator}/transaction/status/{transaction_id}", timeout=5)
        return (response.content, response.status_code, response.headers.items())
    except:
        return jsonify({"error": "Coordinator unreachable"}), 503

@app.route('/api/wallet/recharge', methods=['POST'])
def recharge_wallet():
    # Direct to Wallet Service
    try:
        response = requests.post(f"{WALLET_SERVICE_URL}/wallet/recharge", json=request.json, timeout=5)
        return (response.content, response.status_code, response.headers.items())
    except:
        return jsonify({"error": "Wallet Service unreachable"}), 503

@app.route('/api/wallet/balance', methods=['GET'])
def get_balance():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400
        
    try:
        response = requests.get(f"{WALLET_SERVICE_URL}/wallet/balance/{user_id}", timeout=5)
        return (response.content, response.status_code, response.headers.items())
    except:
        return jsonify({"error": "Wallet Service unreachable"}), 503

@app.route('/api/transactions/history', methods=['GET'])
def transaction_history():
    user_id = request.args.get('user_id')
    try:
        response = requests.get(f"{WALLET_SERVICE_URL}/wallet/history/{user_id}", timeout=5)
        return (response.content, response.status_code, response.headers.items())
    except:
        return jsonify({"error": "Wallet Service unreachable"}), 503

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5001, help="Port to run on")
    parser.add_argument("--name", type=str, default="PaymentAPI-1", help="Server Name")
    args = parser.parse_args()
    
    PORT = args.port
    SERVER_NAME = args.name
    logger = LoggingClient(SERVER_NAME)
    
    print(f"Starting {SERVER_NAME} on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
