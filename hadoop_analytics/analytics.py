import os
import subprocess
import time
import csv
from pymongo import MongoClient, errors
from pymongo.errors import ConnectionFailure

# --- Configuration ---
# This script runs from the 'hadoop_analytics' directory
MONGO_URI = "mongodb://localhost:28000/" # Your Docker DB port
HADOOP_COMPOSE_FILE = "docker-compose-hadoop.yml"
TEMP_CSV_FILE = "temp_jobs.csv"
JAVA_SOURCE_PATH = "java_mapreduce/MaxJobStatus.java"
JAVA_CONTAINER_PATH = "/tmp/MaxJobStatus.java"
JAR_CONTAINER_PATH = "/tmp/MaxJobStatus.jar"
CSV_CONTAINER_PATH = "/tmp/jobs.csv"
HDFS_INPUT_DIR = "/input_data"
HDFS_OUTPUT_DIR = "/output_data"

# --- Helper Functions for Logging ---
# We're not using the RPC logger here, as this is a separate batch process
# We'll just print to stdout, which the API server's process will capture.
def log(message):
    """Prints a formatted log message."""
    print(f"[{time.strftime('%H:%M:%S')}] ANALYTICS: {message}")

def log_command(command_str):
    """Prints and executes a shell command."""
    log(f"Running command: {command_str}")
    # We use os.system for simplicity, as it prints stdout/stderr directly
    # For production, subprocess.run with error checking is better.
    return os.system(command_str)

# --- Main Analytics Pipeline ---
def run_analytics_pipeline():
    """
    Executes the full MapReduce pipeline.
    """
    db = None
    try:
        # --- 1. Connect to MongoDB and Export Data ---
        log("Connecting to MongoDB...")
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        db = client.vidflow_db
        log("Fetching video data from 'videos' collection...")
        
        videos = list(db.videos.find())
        if not videos:
            log("No video data found. Aborting.")
            return

        log(f"Exporting {len(videos)} documents to {TEMP_CSV_FILE}...")
        
        # Create the CSV file
        with open(TEMP_CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            # Write header per the plan (5th column/index 4 must be status)
            writer.writerow(["job_id", "user_id", "resolution", "processing_time", "status", "file_size"])
            for doc in videos:
                writer.writerow([
                    str(doc.get('_id')),
                    doc.get('owner_id', 'unknown'),
                    '1080p', # Dummy data
                    '10',    # Dummy data
                    doc.get('status', 'UNKNOWN'),
                    '100'    # Dummy data
                ])
        log("CSV file created successfully.")

        # --- 2. Start Hadoop Cluster ---
        log("Starting Hadoop cluster (this may take a minute)...")
        if log_command(f"docker-compose -f {HADOOP_COMPOSE_FILE} up -d --build") != 0:
            raise Exception("Failed to start Hadoop cluster.")
        log("Hadoop cluster started. Waiting 10s for services...")
        time.sleep(10) # Give services time to initialize

        # --- 3. Compile Java Code ---
        log("Compiling Java MapReduce code...")
        log_command(f"docker cp {JAVA_SOURCE_PATH} namenode:{JAVA_CONTAINER_PATH}")
        
        compile_cmd = (
            "docker exec namenode bash -c \""
            "CLASSPATH_HADOOP=$(hadoop classpath) && "
            "javac -classpath \\\"$CLASSPATH_HADOOP\\\" -d /tmp {JAVA_CONTAINER_PATH} && "
            "jar -cvf {JAR_CONTAINER_PATH} -C /tmp ."
            "\""
        ).format(JAVA_CONTAINER_PATH=JAVA_CONTAINER_PATH, JAR_CONTAINER_PATH=JAR_CONTAINER_PATH)
        
        if log_command(compile_cmd) != 0:
            raise Exception("Failed to compile Java code.")
        log("Java code compiled and JAR created.")

        # --- 4. Load Data into HDFS ---
        log("Loading data into HDFS...")
        log_command(f"docker cp {TEMP_CSV_FILE} namenode:{CSV_CONTAINER_PATH}")
        # Clean up HDFS directories (ignore errors if they don't exist)
        log_command(f"docker exec namenode hdfs dfs -rm -r {HDFS_INPUT_DIR} || true")
        log_command(f"docker exec namenode hdfs dfs -rm -r {HDFS_OUTPUT_DIR} || true")
        # Create input directory and put the file
        log_command(f"docker exec namenode hdfs dfs -mkdir -p {HDFS_INPUT_DIR}")
        log_command(f"docker exec namenode hdfs dfs -put {CSV_CONTAINER_PATH} {HDFS_INPUT_DIR}/")
        log("Data loaded into HDFS.")

        # --- 5. Run MapReduce Job ---
        log("Running MapReduce Job...")
        mapreduce_cmd = (
            "docker exec namenode hadoop jar {JAR_CONTAINER_PATH} "
            "MaxJobStatus {HDFS_INPUT_DIR} {HDFS_OUTPUT_DIR}"
        ).format(
            JAR_CONTAINER_PATH=JAR_CONTAINER_PATH,
            HDFS_INPUT_DIR=HDFS_INPUT_DIR,
            HDFS_OUTPUT_DIR=HDFS_OUTPUT_DIR
        )
        if log_command(mapreduce_cmd) != 0:
            raise Exception("MapReduce job failed.")
        log("MapReduce job completed.")

        # --- 6. Fetch Results ---
        log("Fetching results from HDFS...")
        result_cmd = f"docker exec namenode hdfs dfs -cat {HDFS_OUTPUT_DIR}/part-r-00000"
        
        # Use subprocess.check_output to capture the stdout
        process = subprocess.run(result_cmd, shell=True, check=True, capture_output=True, text=True)
        result_text = process.stdout
        log(f"Raw result:\n{result_text}")

        # --- 7. Parse Results and Update Cache ---
        log("Parsing results and updating dashboard cache...")
        status_counts = {"last_updated": int(time.time())}
        for line in result_text.strip().split('\n'):
            if line:
                status, count = line.split('\t') # Hadoop's default separator is tab
                status_counts[status.strip()] = int(count.strip())
        
        log(f"Parsed counts: {status_counts}")
        
        # Update the cache in MongoDB (using update_one with upsert=True)
        db.analytics_cache.update_one(
            {"_id": "job_status_counts"},
            {"$set": status_counts},
            upsert=True
        )
        log("Analytics cache updated in MongoDB.")

    except Exception as e:
        log(f"FATAL ERROR in analytics pipeline: {e}")
    
    finally:
        # --- 8. Shut Down Hadoop Cluster ---
        log("Shutting down Hadoop cluster...")
        log_command(f"docker-compose -f {HADOOP_COMPOSE_FILE} down -v")
        log("Analytics run finished.")
        # Clean up local temp file
        if os.path.exists(TEMP_CSV_FILE):
            os.remove(TEMP_CSV_FILE)

if __name__ == "__main__":
    run_analytics_pipeline()