import requests
import threading
import time
import redis
import jwt
from flask import Flask, request, jsonify
from flask_cors import CORS
from logging_client import LoggingClient

app = Flask(__name__)
logger = LoggingClient("ApiGateway")
CORS(app)

# --- Configuration ---
import os
import json

# --- Configuration ---
# The backend API servers we will balance between
API_SERVERS = json.loads(os.getenv("API_SERVERS", '["http://localhost:5001", "http://localhost:5002"]'))

# Redis for Rate Limiting
redis_client = redis.Redis(host=os.getenv("REDIS_HOST", 'localhost'), port=6379, db=0)

# JWT Secret
JWT_SECRET = "phonepay_secret_key"

# --- Load Balancer State (Exp 7) ---
server_index = 0
index_lock = threading.Lock()

request_counts = {server: 0 for server in API_SERVERS}
count_lock = threading.Lock()

# --- Helper Functions ---

def check_rate_limit(ip_address):
    """
    Rate limiting: 100 requests per minute per IP.
    """
    key = f"rate_limit:{ip_address}"
    current = redis_client.get(key)
    
    if current and int(current) > 100:
        return False
    
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, 60) # Reset every minute
    pipe.execute()
    return True

def validate_token(token):
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# --- Admin Endpoints ---

@app.route('/admin/lb-stats', methods=['GET'])
def get_lb_stats():
    with count_lock:
        stats = {
            "api_server_1": {
                "port": 5001,
                "requests": request_counts.get("http://localhost:5001", 0)
            },
            "api_server_2": {
                "port": 5002,
                "requests": request_counts.get("http://localhost:5002", 0)
            }
        }
    return jsonify(stats)

@app.route('/admin/system-status', methods=['GET'])
def get_system_status():
    status = {}
    
    def ping_service(url, service_name):
        try:
            requests.get(url, timeout=0.5)
            return "ONLINE"
        except:
            return "OFFLINE"
            
    status["payment_api_1"] = ping_service(f"{API_SERVERS[0]}/health", "Payment API 1")
    status["payment_api_2"] = ping_service(f"{API_SERVERS[1]}/health", "Payment API 2")
    status["coordinator_primary"] = ping_service(os.getenv("COORDINATOR_URL", "http://localhost:6000") + "/health", "Primary Coordinator")
    status["coordinator_backup"] = ping_service(os.getenv("BACKUP_COORDINATOR_URL", "http://localhost:6001") + "/health", "Backup Coordinator")
    status["wallet_service"] = ping_service(os.getenv("WALLET_SERVICE_URL", "http://localhost:6100") + "/health", "Wallet Service")
    status["merchant_service"] = ping_service(os.getenv("MERCHANT_SERVICE_URL", "http://localhost:6200") + "/health", "Merchant Service")
    status["fraud_service"] = ping_service(os.getenv("FRAUD_SERVICE_URL", "http://localhost:7100") + "/health", "Fraud Service")
    
    return jsonify(status)

@app.route('/admin/kill-coordinator', methods=['POST'])
def kill_coordinator():
    try:
        coord_url = os.getenv("COORDINATOR_URL", "http://localhost:6000")
        requests.post(f"{coord_url}/simulate/kill", timeout=1)
        return jsonify({"status": "SUCCESS", "message": "Primary Coordinator Killed"})
    except:
        return jsonify({"error": "Failed to reach coordinator"}), 500

@app.route('/admin/simulate-lag', methods=['POST'])
def simulate_lag():
    try:
        coord_url = os.getenv("COORDINATOR_URL", "http://localhost:6000")
        requests.post(f"{coord_url}/simulate/lag", timeout=1)
        return jsonify({"status": "SUCCESS", "message": "Network Lag Simulated"})
    except:
        return jsonify({"error": "Failed to reach coordinator"}), 500

@app.route('/admin/reset-system', methods=['POST'])
def reset_system():
    try:
        coord_url = os.getenv("COORDINATOR_URL", "http://localhost:6000")
        requests.post(f"{coord_url}/simulate/reset", timeout=1)
        return jsonify({"status": "SUCCESS", "message": "System Reset"})
    except:
        return jsonify({"error": "Failed to reach coordinator"}), 500

# --- Auth Endpoints ---

@app.route('/auth/login', methods=['POST'])
def login():
    # Forward to Wallet Service (which handles users) or handle here?
    # For simplicity, let's assume Wallet Service handles user auth
    # But wait, Gateway usually handles auth.
    # Let's mock it here for now or forward to a user service.
    # The prompt says "Wallet Service: Manage user wallet balances".
    # Let's assume we forward to Wallet Service for verification.
    
    # Forwarding to Wallet Service for user verification
    # We'll implement /user/login in Wallet Service
    try:
        wallet_url = os.getenv("WALLET_SERVICE_URL", "http://localhost:6100")
        response = requests.post(f"{wallet_url}/user/login", json=request.json)
        return (response.content, response.status_code, response.headers.items())
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Wallet Service unavailable"}), 503

@app.route('/auth/register', methods=['POST'])
def register():
    try:
        wallet_url = os.getenv("WALLET_SERVICE_URL", "http://localhost:6100")
        response = requests.post(f"{wallet_url}/user/register", json=request.json)
        return (response.content, response.status_code, response.headers.items())
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Wallet Service unavailable"}), 503

# --- Main Gateway Logic ---

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def gateway(path):
    global server_index
    
    # 1. Rate Limiting
    if not check_rate_limit(request.remote_addr):
        return jsonify({"error": "Rate limit exceeded"}), 429
        
    # 2. Auth Validation (Skip for auth endpoints and admin)
    if not (path.startswith('auth/') or path.startswith('admin/')):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Missing Authorization header"}), 401
        
        # Remove 'Bearer ' prefix
        if token.startswith('Bearer '):
            token = token.split(' ')[1]
            
        user_data = validate_token(token)
        if not user_data:
            return jsonify({"error": "Invalid token"}), 401
            
        # Add user info to headers for downstream services
        # request.headers['X-User-ID'] = user_data['user_id'] # This is tricky with requests, better to pass in body or query if possible, or just forward header
    
    # 3. Load Balancing
    with index_lock:
        target_server = API_SERVERS[server_index]
        server_index = (server_index + 1) % len(API_SERVERS)
        
    with count_lock:
        request_counts[target_server] += 1
        
    print(f"[{time.strftime('%H:%M:%S')}] Forwarding {path} to {target_server}")
    logger.log(f"Forwarding {request.method} {path} to {target_server}")
    
    # 4. Forward Request
    try:
        # Prepare headers (exclude Host)
        headers = {key: value for key, value in request.headers if key != 'Host'}
        
        response = requests.request(
            method=request.method,
            url=f"{target_server}/{path}",
            params=request.args,
            data=request.get_data(),
            headers=headers,
            timeout=10
        )
        
        # Exclude hop-by-hop headers
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in response.raw.headers.items()
                   if name.lower() not in excluded_headers]
                   
        return (response.content, response.status_code, headers)
        
    except requests.exceptions.ConnectionError:
        return jsonify({"error": f"Service at {target_server} is unreachable"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Starting API Gateway on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)