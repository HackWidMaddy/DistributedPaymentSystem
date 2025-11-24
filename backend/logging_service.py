import xmlrpc.server
import threading
import time
from flask import Flask, jsonify

# We need a separate thread for Flask to handle health checks
# because xmlrpc.server.SimpleXMLRPCServer is blocking.

class LoggingService:
    def __init__(self):
        self.logs = []
        self.lamport_clock = 0
        self.lock = threading.Lock()
    
    def log_message(self, service_name, message, client_clock):
        with self.lock:
            # Update Lamport clock
            self.lamport_clock = max(self.lamport_clock, client_clock) + 1
            
            log_entry = {
                "service": service_name,
                "message": message,
                "lamport_clock": self.lamport_clock,
                "timestamp": time.time()
            }
            self.logs.append(log_entry)
            
            print(f"[LOG] {service_name}: {message} (LC: {self.lamport_clock})")
            return self.lamport_clock

    def get_logs(self):
        return self.logs

# --- Flask App for Health Check & Viewing Logs ---
app = Flask(__name__)
logging_service = LoggingService()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ONLINE", "service": "LoggingService"})

@app.route('/logs', methods=['GET'])
def get_logs():
    return jsonify(logging_service.get_logs())

def run_flask():
    app.run(host='0.0.0.0', port=7001, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Start Flask in a separate thread
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("Starting RPC Logging Service on port 7000...")
    server = xmlrpc.server.SimpleXMLRPCServer(("0.0.0.0", 7000), allow_none=True)
    server.register_instance(logging_service)
    server.serve_forever()