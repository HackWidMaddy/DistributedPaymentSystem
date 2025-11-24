import argparse
import time
import random
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- Configuration ---
PORT = 7100

# --- Helper Functions ---

def calculate_fraud_score(user_id, amount):
    # Mock Logic
    score = 0.0
    
    # Rule 1: High Amount
    if amount > 10000:
        score += 0.4
        
    # Rule 2: Random check (simulating ML model)
    if random.random() < 0.1:
        score += 0.3
        
    # Rule 3: Blacklisted user (mock)
    if user_id == "hacker":
        score = 1.0
        
    return min(score, 1.0)

# --- Endpoints ---

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ONLINE", "service": "FraudService"})

@app.route('/check', methods=['POST'])
def check_fraud():
    data = request.json
    user_id = data.get('user_id')
    amount = float(data.get('amount', 0))
    
    score = calculate_fraud_score(user_id, amount)
    
    return jsonify({
        "user_id": user_id,
        "amount": amount,
        "fraud_score": score,
        "status": "BLOCKED" if score > 0.8 else "ALLOWED"
    })

if __name__ == "__main__":
    print(f"Starting Fraud Detection Service on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
