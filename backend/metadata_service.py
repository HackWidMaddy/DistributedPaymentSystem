import os
import time
import threading
import argparse
import requests
from flask import Flask, request, jsonify
from pymongo import MongoClient, errors
from pymongo.errors import ConnectionFailure

# --- Configuration ---
# Removed hardcoded ports, will be passed as args
MONGO_URI = "mongodb://localhost:28000/"  # Your Docker DB port
HEARTBEAT_INTERVAL = 2  # Primary sends heartbeat every 2 seconds
FAILOVER_TIMEOUT = 5  # Backup promotes itself if no heartbeat in 5 seconds

# --- Global State ---
app = Flask(__name__)
db = None  # Will be initialized in main
IS_PRIMARY = False
PEER_URL = None # This will be set at startup (e.g., http://localhost:6001)
MY_PORT = 0 # This will be set at startup

# This is a thread-safe way to store the last heartbeat time
last_heartbeat_lock = threading.Lock()
last_heartbeat_time = time.time()

# --- Primary Logic (Heartbeat Sender) ---
def send_heartbeat():
    """
    Called by the Primary. Runs in a background thread.
    Continuously sends a heartbeat to the PEER.
    """
    while IS_PRIMARY:
        try:
            requests.post(f"{PEER_URL}/heartbeat", timeout=1)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            print(f"[{time.strftime('%H:%M:%S')}] WARN: Peer service at {PEER_URL} is down.")
        
        time.sleep(HEARTBEAT_INTERVAL)

# --- Backup Logic (Health Checker) ---
def check_primary_health():
    """
    Called by the Backup. Runs in a background thread.
    Checks if the Primary is still alive.
    """
    global IS_PRIMARY
    global last_heartbeat_time
    
    while not IS_PRIMARY:
        time.sleep(1) # Check every second
        
        with last_heartbeat_lock:
            time_since_last_heartbeat = time.time() - last_heartbeat_time
            
        if time_since_last_heartbeat > FAILOVER_TIMEOUT:
            print(f"[{time.strftime('%H:%M:%S')}] !!! PRIMARY TIMEOUT !!!")
            print(f"[{time.strftime('%H:%M:%S')}] Promoting to PRIMARY.")
            IS_PRIMARY = True
            # When this node is promoted, it must start sending heartbeats to its peer (the old primary)
            # to detect if it ever comes back online (though we don't implement rejoin logic here)
            thread = threading.Thread(target=send_heartbeat, daemon=True)
            thread.start()

# --- Database Connection ---
def get_db():
    global db
    if db is None:
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            client.server_info() # Force connection check
            db = client.vidflow_db
            print("Successfully connected to MongoDB.")
        except ConnectionFailure:
            print(f"FATAL: Could not connect to MongoDB at {MONGO_URI}")
            os._exit(1)
    return db

# --- Shared API Endpoints ---
@app.before_request
def check_primary_status():
    allowed_endpoints = ['heartbeat', 'replicate', 'debug_kill', 'static']
    if request.endpoint not in allowed_endpoints:
        if not IS_PRIMARY:
            return jsonify({"error": "This is a backup node. Please contact the primary."}), 403

# --- Public API Routes (Blocked on Backup) ---

@app.route('/api/videos', methods=['POST'])
def create_video_entry():
    data = request.json
    db = get_db()
    
    new_video = {
        "title": data.get("title"),
        "filename": data.get("filename"),
        "owner_id": data.get("username"),
        "status": "PENDING",
        "storage_path": data.get("storage_path"),
        "transcoded_path": None,
        "uploaded_at": time.time()
    }

    # 2. Replicate to Peer *FIRST*
    print(f"[{time.strftime('%H:%M:%S')}] PRIMARY: Replicating {new_video['filename']} to peer ({PEER_URL})...")
    try:
        replicate_data = {"type": "video", "document": new_video}
        response = requests.post(f"{PEER_URL}/replicate", json=replicate_data, timeout=2)
        if response.status_code != 200:
            print(f"[{time.strftime('%H:%M:%S')}] FATAL: Peer replication failed. Status: {response.status_code}")
            return jsonify({"error": "Peer replication failed. Write aborted to maintain consistency."}), 500
    
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # This is now *expected* behavior if the peer is dead (e.g., after failover)
        print(f"[{time.strftime('%H:%M:%S')}] WARN: Peer node is down. Proceeding without replication.")
        # We will proceed with the write, as we are the only active node.
    
    print(f"[{time.strftime('%H:%M:%S')}] PRIMARY: Backup acknowledged (or peer down). Writing to primary DB.")
    
    # 3. Write to Primary's own DB
    result = db.videos.insert_one(new_video)
    new_video["_id"] = str(result.inserted_id)
    return jsonify(new_video), 201

@app.route('/api/videos', methods=['GET'])
def get_videos():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "username query parameter is required"}), 400
        
    db = get_db()
    videos = []
    for video in db.videos.find({"owner_id": username}):
        video["_id"] = str(video["_id"])
        videos.append(video)
        
    return jsonify(videos), 200

@app.route('/api/videos/<string:video_id>', methods=['PUT'])
def update_video_status(video_id):
    data = request.json
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "status is required"}), 400

    print(f"[{time.strftime('%H:%M:%S')}] PRIMARY: Replicating status update for {video_id} to peer ({PEER_URL})...")
    
    # 1. Replicate to Peer *FIRST*
    try:
        replicate_data = {"type": "status_update", "video_id": video_id, "status": new_status}
        response = requests.post(f"{PEER_URL}/replicate", json=replicate_data, timeout=2)
        if response.status_code != 200:
            return jsonify({"error": "Peer replication failed. Write aborted."}), 500
    
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        print(f"[{time.strftime('%H:%M:%S')}] WARN: Peer node is down. Proceeding without replication.")
        # Proceed with the write
        
    # 2. Write to Primary's own DB
    print(f"[{time.strftime('%H:%M:%S')}] PRIMARY: Backup acknowledged (or peer down). Updating primary DB.")
    db = get_db()
    result = db.videos.update_one(
        {"filename": video_id},
        {"$set": {"status": new_status}}
    )

    if result.matched_count == 0:
        from bson.objectid import ObjectId
        try:
            result_by_id = db.videos.update_one(
                {"_id": ObjectId(video_id)},
                {"$set": {"status": new_status}}
            )
            if result_by_id.matched_count == 0:
                return jsonify({"error": f"Video not found by filename or ID: {video_id}"}), 404
        except Exception:
             return jsonify({"error": f"Video not found and invalid ID format: {video_id}"}), 404

    return jsonify({"message": f"Status for {video_id} updated to {new_status}"}), 200


# --- Internal Routes (Allowed on Backup) ---

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    global last_heartbeat_time
    if not IS_PRIMARY: # Only backups should track heartbeats
        with last_heartbeat_lock:
            last_heartbeat_time = time.time()
    return jsonify({"status": "ok"}), 200

@app.route('/replicate', methods=['POST'])
def replicate():
    """
    [BACKUP-ONLY] The Primary calls this to synchronously replicate a write.
    """
    # This check is now crucial to prevent a Primary from replicating to itself
    if IS_PRIMARY: 
        return jsonify({"error": "I am a primary, I cannot replicate."}), 400

    # This is the "ACK"
    # We do NOT write to the DB, as the Primary handles all writes.
    
    data = request.json
    if data['type'] == 'video':
        print(f"[{time.strftime('%H:%M:%S')}] BACKUP: ACK'ing replication for {data['document']['filename']}.")
    elif data['type'] == 'status_update':
        print(f"[{time.strftime('%H:%M:%S')}] BACKUP: ACK'ing status update for {data['video_id']}.")
        
    return jsonify({"status": "replicated"}), 200

@app.route('/admin/kill-primary', methods=['POST'])
def debug_kill():
    # We can only kill the *real* primary
    if MY_PORT != 6000:
        return jsonify({"error": "I am a backup, I can't be killed (from this endpoint)"}), 400
        
    print(f"[{time.strftime('%H:%M:%S')}] !!! ADMIN: Received /admin/kill-primary signal. Terminating. !!!")
    
    def delayed_kill():
        time.sleep(0.1)
        os._exit(1)
        
    threading.Thread(target=delayed_kill).start()
    return jsonify({"message": "Primary metadata service terminate signal sent."}), 200

# --- Main Application Runner ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Primary-Backup Metadata Service")
    parser.add_argument("--role", required=True, choices=["primary", "backup"], help="The role of this node.")
    parser.add_argument("--port", type=int, required=True, help="The port to run this service on.")
    parser.add_argument("--peer", required=True, help="The full URL of the peer node (e.g., http://localhost:6001).")
    args = parser.parse_args()

    # Set global state from args
    PEER_URL = args.peer
    MY_PORT = args.port
    
    get_db() # Initialize DB connection on startup

    if args.role == "primary":
        IS_PRIMARY = True
        # Start the heartbeat thread
        thread = threading.Thread(target=send_heartbeat, daemon=True)
        thread.start()
        print(f"Starting PRIMARY service on port {MY_PORT} (Peer: {PEER_URL})")
    else:
        IS_PRIMARY = False
        last_heartbeat_time = time.time() # Initialize heartbeat time
        # Start the health check thread
        thread = threading.Thread(target=check_primary_health, daemon=True)
        thread.start()
        print(f"Starting BACKUP service on port {MY_PORT} (Peer: {PEER_URL})")

    app.run(host='0.0.0.0', port=MY_PORT, debug=False, use_reloader=False)