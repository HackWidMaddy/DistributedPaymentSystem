import argparse
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

import os

# --- Configuration ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:28000/")
PORT = 6200

# --- Database Setup ---
client = MongoClient(MONGO_URI)
db = client.payflow
merchants_col = db.merchants
settlements_col = db.settlements

# --- Endpoints ---

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ONLINE", "service": "MerchantService"})

@app.route('/merchant/register', methods=['POST'])
def register():
    data = request.json
    if merchants_col.find_one({"email": data['email']}):
        return jsonify({"error": "Merchant already exists"}), 400
        
    data['balance'] = 0.0
    data['created_at'] = time.time()
    merchants_col.insert_one(data)
    return jsonify({"status": "SUCCESS"})

@app.route('/merchant/settlements', methods=['GET'])
def get_settlements():
    merchant_id = request.args.get('merchant_id')
    settlements = list(settlements_col.find({"merchant_id": merchant_id}, {"_id": 0}))
    return jsonify(settlements)

@app.route('/merchant/payout', methods=['POST'])
def trigger_payout():
    # In a real system, this would trigger a bank transfer
    # Here we just record it
    data = request.json
    merchant_id = data['merchant_id']
    amount = data['amount']
    
    settlements_col.insert_one({
        "merchant_id": merchant_id,
        "amount": amount,
        "status": "PROCESSED",
        "timestamp": time.time()
    })
    
    return jsonify({"status": "SUCCESS"})

if __name__ == "__main__":
    print(f"Starting Merchant Service on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
