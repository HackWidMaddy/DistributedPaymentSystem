import os
import time
import argparse
import requests
import subprocess
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from werkzeug.utils import secure_filename
from bson import json_util # For serializing MongoDB ObjectIds

# Import our RPC logging client
from logging_client import LoggingClient

# --- Configuration ---
MONGO_URI = "mongodb://localhost:28000/"
METADATA_PRIMARY = "http://localhost:6000"
METADATA_BACKUP = "http://localhost:6001"
VIDEO_STORAGE_PATH = os.path.join(os.getcwd(), "storage", "raw")

# --- Global State ---
app = Flask(__name__)
CORS(app) # Allow requests from the gateway
db = None
logger = None # Will be initialized in main

# --- Database Connection ---
def get_db():
    """Initializes and returns the MongoDB database connection."""
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

# --- Helper to serialize Mongo data ---
def mongo_to_json(data):
    """Converts MongoDB documents (with ObjectIds) to JSON-safe strings."""
    return json_util.dumps(data)

# --- API Endpoints ---

@app.route('/api/health', methods=['GET'])
def health_check():
    """A simple health check endpoint for the gateway."""
    return jsonify({"status": "ok"}), 200

@app.route('/api/upload', methods=['POST'])
def upload_video():
    """
    Handles file upload from the user.
    1. Saves the file to local storage.
    2. Calls the Metadata Service (with failover) to create an entry.
    """
    logger.log("Received /api/upload request.")
    
    try:
        # 1. Get data from the multipart form
        if 'videoFile' not in request.files:
            return jsonify({"error": "No 'videoFile' part in request."}), 400
            
        file = request.files['videoFile']
        title = request.form['title']
        username = request.form['username']
        
        if file.filename == '':
            return jsonify({"error": "No selected file."}), 400

        # 2. Save the file to ./storage/raw
        filename = secure_filename(file.filename)
        save_path = os.path.join(VIDEO_STORAGE_PATH, filename)
        file.save(save_path)
        logger.log(f"File '{filename}' saved to {save_path}.")

        # 3. Call Metadata Service (with Failover - Exp 9)
        metadata_payload = {
            "title": title,
            "filename": filename,
            "username": username,
            "storage_path": save_path
        }
        
        response = None
        try:
            # First, try the Primary
            logger.log("Calling Primary Metadata Service...")
            response = requests.post(f"{METADATA_PRIMARY}/api/videos", json=metadata_payload, timeout=10)
            response.raise_for_status() # Raise an exception for 4xx/5xx errors
            
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            # If Primary fails, try the Backup
            logger.log("WARN: Primary Metadata Service is down. Failing over to Backup.")
            try:
                response = requests.post(f"{METADATA_BACKUP}/api/videos", json=metadata_payload, timeout=10)
                response.raise_for_status()
            except Exception as e:
                logger.log(f"FATAL: Backup Metadata Service also failed. {e}")
                return jsonify({"error": "Upload failed. All metadata services are down."}), 500
        
        except requests.exceptions.RequestException as e:
            # Handle non-connection errors (e.g., 500 from primary)
            logger.log(f"ERROR: Metadata service returned error: {e}")
            return jsonify({"error": f"Metadata service error: {e}"}), (response.status_code if response else 500)

        logger.log("Video metadata entry created successfully.")
        return jsonify({
            "message": "Video upload successful. Status: PENDING",
            "video_id": response.json().get("_id")
        }), 201

    except Exception as e:
        logger.log(f"ERROR: Unknown error in /api/upload: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/videos', methods=['GET'])
def get_user_videos():
    """
    Fetches the list of videos for a user.
    Calls the Metadata Service (with failover).
    """
    username = request.args.get("username")
    logger.log(f"Received /api/videos request for user: {username}.")
    
    if not username:
        return jsonify({"error": "username query parameter is required"}), 400
        
    try:
        # First, try the Primary
        response = requests.get(f"{METADATA_PRIMARY}/api/videos", params={"username": username}, timeout=10)
        if response.status_code == 403: # 403 means "I am a backup"
             raise requests.exceptions.ConnectionError("Primary is actually backup")

        response.raise_for_status()
        
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # If Primary fails, try the Backup
        logger.log("WARN: Primary Metadata Service is down. Failing over to Backup.")
        try:
            response = requests.get(f"{METADATA_BACKUP}/api/videos", params={"username": username}, timeout=10)
            response.raise_for_status()
        except Exception as e:
            logger.log(f"FATAL: Backup Metadata Service also failed. {e}")
            return jsonify({"error": "Failed to fetch videos. All metadata services are down."}), 500

    logger.log(f"Successfully fetched {len(response.json())} videos for {username}.")
    return response.json(), 200 # Return the JSON array directly

# --- Admin Endpoints (Handled by API Server) ---

@app.route('/admin/logs', methods=['GET'])
def get_admin_logs():
    """Fetches the last 50 logs from the DB, sorted by Lamport clock."""
    logger.log("Admin requested logs from /admin/logs.")
    db = get_db()
    
    try:
        logs = list(db.distributed_logs.find().sort("lamport_clock", -1).limit(50))
        # We sort by -1 (descending) to get the *latest* logs
        # Then reverse in Python to show oldest-to-newest in the UI
        logs.reverse() 
        
        # We must use our special JSON serializer
        return app.response_class(
            response=mongo_to_json(logs),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.log(f"ERROR: Could not fetch logs from DB. {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/analytics', methods=['GET'])
def get_analytics_cache():
    """Fetches the cached MapReduce results from the DB."""
    logger.log("Admin requested analytics from /admin/analytics.")
    db = get_db()
    
    data = db.analytics_cache.find_one({"_id": "job_status_counts"})
    if data:
        # Use our special JSON serializer
        return app.response_class(
            response=mongo_to_json(data),
            status=200,
            mimetype='application/json'
        )
    else:
        # Return default structure per frontend plan
        return jsonify({
            "COMPLETED": 0, "PENDING": 0, "FAILED": 0, "PROCESSING": 0,
            "last_updated": "Never"
        })

@app.route('/admin/kill-primary', methods=['POST'])
def kill_primary():
    """Sends the "kill" signal to the Primary Metadata Service."""
    logger.log("ADMIN: Received request to kill primary metadata service.")
    
    try:
        # We *only* target the primary for this request. No failover.
        response = requests.post(f"{METADATA_PRIMARY}/admin/kill-primary", timeout=2)
        return response.json(), response.status_code
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        logger.log("ADMIN: Kill signal failed. Primary is already down.")
        return jsonify({"error": "Primary metadata service is already unreachable."}), 404

@app.route('/admin/run-analytics', methods=['POST'])
def run_analytics():
    """
    Triggers the standalone analytics.py script in a non-blocking way.
    """
    logger.log("ADMIN: Received request to run analytics job.")

    # --- START OF FIX ---
    # Find the python.exe *inside our venv*
    backend_dir = os.path.dirname(__file__)
    python_exe_path = os.path.join(backend_dir, 'venv', 'Scripts', 'python.exe')

    # Check if the venv python exists
    if not os.path.exists(python_exe_path):
        logger.log(f"FATAL: Could not find venv python at {python_exe_path}")
        # Fallback to just "python", though it may fail
        python_exe_path = "python"

    # --- END OF FIX ---

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    script_path = os.path.join(project_root, 'hadoop_analytics', 'analytics.py')

    try:
        # Use subprocess.Popen for a non-blocking call.
        subprocess.Popen(
            [python_exe_path, script_path], # Use the full venv path
            cwd=os.path.join(project_root, 'hadoop_analytics') 
        )

        logger.log("Analytics job started in the background.")

        return jsonify({
            "message": "Analytics job started. This may take a minute. The dashboard will update when complete."
        }), 202

    except FileNotFoundError:
        logger.log(f"FATAL: analytics.py not found at {script_path}")
        return jsonify({"error": "analytics.py script not found."}), 500
    except Exception as e:
        logger.log(f"ERROR: Could not start analytics job. {e}")
        return jsonify({"error": str(e)}), 500
    
# --- Main Application Runner ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VidFlow API Server")
    parser.add_argument("--port", type=int, required=True, help="Port to run this server on.")
    parser.add_argument("--name", type=str, required=True, help="Service name for logging.")
    args = parser.parse_args()

    # Initialize our services
    get_db()
    logger = LoggingClient(service_name=args.name)
    
    print(f"Starting API Server '{args.name}' on port {args.port}...")
    
    # Run the Flask app
    # use_reloader=False is important for stability with background threads/subprocesses
    app.run(host='0.0.0.0', port=args.port, debug=False, use_reloader=False)