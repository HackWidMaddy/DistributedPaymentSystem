import os
import time
import requests
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Import our RPC logging client
from logging_client import LoggingClient

# --- Configuration ---
MONGO_URI = "mongodb://localhost:28000/"
METADATA_PRIMARY = "http://localhost:6000"
METADATA_BACKUP = "http://localhost:6001"
POLL_INTERVAL = 3 # Check for new jobs every 3 seconds
PROCESSING_TIME = 5 # Simulate 5 seconds of "work"

# --- Global State ---
db = None
logger = LoggingClient(service_name="Transcoder-Worker")

# --- Database Connection ---
def get_db():
    """Initializes and returns the MongoDB database connection."""
    global db
    if db is None:
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            client.server_info() # Force connection check
            db = client.vidflow_db
            logger.log("Successfully connected to MongoDB.")
        except ConnectionFailure:
            logger.log(f"FATAL: Could not connect to MongoDB at {MONGO_URI}")
            os._exit(1)
    return db

# --- Helper Function to Update Status ---
def update_video_status(video_filename, new_status):
    """
    Calls the Metadata Service (with failover) to update a video's status.
    This demonstrates client-side failover (Exp 9).
    """
    logger.log(f"Updating status for {video_filename} to {new_status}.")
    
    metadata_payload = {"status": new_status}
    
    # We pass the filename in the URL, as per the metadata_service PUT route
    # Note: Our metadata_service is built to also check by _id if filename fails
    url_path = f"/api/videos/{video_filename}"
    
    try:
        # First, try the Primary
        response = requests.put(f"{METADATA_PRIMARY}{url_path}", json=metadata_payload, timeout=10)
        if response.status_code == 403: # 403 means "I am a backup"
             raise requests.exceptions.ConnectionError("Primary is actually backup")
        response.raise_for_status()
        
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # If Primary fails, try the Backup
        logger.log(f"WARN: Primary Metadata Service is down. Failing over to Backup.")
        try:
            response = requests.put(f"{METADATA_BACKUP}{url_path}", json=metadata_payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            logger.log(f"FATAL: Backup Metadata Service also failed. {e}")
            return False # Indicate failure
            
    logger.log(f"Status for {video_filename} updated successfully.")
    return True # Indicate success

# --- Main Worker Loop ---
def start_worker():
    """
    The main polling loop for the transcoder.
    """
    db = get_db()
    logger.log("Transcoder worker started. Polling for jobs...")
    
    while True:
        try:
            # 1. Find a job
            job = db.videos.find_one({"status": "PENDING"})
            
            if job:
                # --- START OF FIX ---
                # We MUST use the unique _id, not the filename
                video_mongo_id = str(job.get('_id')) 
                filename_for_log = job.get('filename') # Just for logging
                
                logger.log(f"Found job: {filename_for_log} (ID: {video_mongo_id})")

                # 2. Set status to "PROCESSING"
                # Pass the unique _id to the update function
                if update_video_status(video_mongo_id, "PROCESSING"):
                
                    # 3. Simulate transcoding work
                    logger.log(f"Simulating transcoding for {filename_for_log}...")
                    time.sleep(PROCESSING_TIME) # This simulates the heavy lifting
                    logger.log(f"Transcoding for {filename_for_log} complete.")
                    
                    # 4. Set status to "COMPLETED"
                    update_video_status(video_mongo_id, "COMPLETED")
                
                else:
                    logger.log(f"Failed to update status for {video_mongo_id}. Will retry.")
                # --- END OF FIX ---
            
            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.log("Shutting down transcoder worker.")
            break
        except Exception as e:
            logger.log(f"ERROR in worker loop: {e}")
            time.sleep(5) # Wait a bit before retrying on error

if __name__ == "__main__":
    start_worker()