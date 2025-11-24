import argparse
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, ReturnDocument
from pymongo.write_concern import WriteConcern
from pymongo.read_concern import ReadConcern

app = Flask(__name__)
CORS(app)

import os

# --- Configuration ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:28000/")
PORT = 6100

# --- Database Setup ---
client = MongoClient(MONGO_URI)
db = client.payflow
wallets_col = db.wallets
ledger_col = db.wallet_ledger
users_col = db.users

# Ensure indexes
wallets_col.create_index("user_id", unique=True)
users_col.create_index("email", unique=True)

# --- Helper Functions ---

def get_wallet(user_id):
    wallet = wallets_col.find_one({"user_id": user_id}, {"_id": 0})
    if not wallet:
        # Create wallet if not exists (for demo simplicity)
        wallet = {"user_id": user_id, "balance": 0.0, "currency": "INR"}
        wallets_col.insert_one(wallet)
        del wallet["_id"]
    return wallet

# --- Endpoints ---

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ONLINE", "service": "WalletService"})

@app.route('/wallet/balance/<user_id>', methods=['GET'])
def get_balance(user_id):
    wallet = get_wallet(user_id)
    return jsonify(wallet)

@app.route('/wallet/history/<user_id>', methods=['GET'])
def get_history(user_id):
    history = list(ledger_col.find({"user_id": user_id}, {"_id": 0}).sort("timestamp", -1).limit(20))
    return jsonify(history)

@app.route('/wallet/debit', methods=['POST'])
def debit_wallet():
    data = request.json
    user_id = data['user_id']
    amount = float(data['amount'])
    transaction_id = data.get('transaction_id', 'unknown')
    
    # ACID Transaction for Debit
    with client.start_session() as session:
        with session.start_transaction(read_concern=ReadConcern('snapshot'), write_concern=WriteConcern(w='majority')):
            # 1. Lock and Update Wallet
            wallet = wallets_col.find_one_and_update(
                {"user_id": user_id, "balance": {"$gte": amount}},
                {"$inc": {"balance": -amount}},
                session=session,
                return_document=ReturnDocument.AFTER
            )
            
            if not wallet:
                session.abort_transaction()
                return jsonify({"error": "Insufficient balance"}), 400
                
            # 2. Record Ledger Entry
            ledger_col.insert_one({
                "user_id": user_id,
                "transaction_id": transaction_id,
                "type": "DEBIT",
                "amount": amount,
                "balance_after": wallet["balance"],
                "timestamp": time.time()
            }, session=session)
            
            session.commit_transaction()
            return jsonify({"status": "SUCCESS", "new_balance": wallet["balance"]})

@app.route('/wallet/credit', methods=['POST'])
def credit_wallet():
    data = request.json
    user_id = data['user_id']
    amount = float(data['amount'])
    transaction_id = data.get('transaction_id', 'unknown')
    
    with client.start_session() as session:
        with session.start_transaction(read_concern=ReadConcern('snapshot'), write_concern=WriteConcern(w='majority')):
            # 1. Update Wallet
            wallet = wallets_col.find_one_and_update(
                {"user_id": user_id},
                {"$inc": {"balance": amount}},
                upsert=True,
                session=session,
                return_document=ReturnDocument.AFTER
            )
            
            # 2. Record Ledger Entry
            ledger_col.insert_one({
                "user_id": user_id,
                "transaction_id": transaction_id,
                "type": "CREDIT",
                "amount": amount,
                "balance_after": wallet["balance"],
                "timestamp": time.time()
            }, session=session)
            
            session.commit_transaction()
            return jsonify({"status": "SUCCESS", "new_balance": wallet["balance"]})

@app.route('/wallet/recharge', methods=['POST'])
def recharge():
    # Same as credit but initiated by user
    return credit_wallet()

# --- User Management (Mock) ---

@app.route('/user/register', methods=['POST'])
def register():
    data = request.json
    if users_col.find_one({"email": data['email']}):
        return jsonify({"error": "User already exists"}), 400
        
    users_col.insert_one(data)
    # Create wallet
    wallets_col.insert_one({"user_id": data['user_id'], "balance": 1000.0, "currency": "INR"}) # Bonus 1000
    return jsonify({"status": "SUCCESS"})

@app.route('/user/login', methods=['POST'])
def login():
    data = request.json
    user = users_col.find_one({"email": data['email']}) # In real app, check password
    if user:
        # Generate token (mock)
        import jwt
        token = jwt.encode({"user_id": user['user_id']}, "phonepay_secret_key", algorithm="HS256")
        return jsonify({"token": token, "user": {"name": user['name'], "user_id": user['user_id']}})
    return jsonify({"error": "Invalid credentials"}), 401

if __name__ == "__main__":
    print(f"Starting Wallet Service on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
