import xmlrpc.client
import threading
import time

import os

LOGGING_SERVICE_URL = os.getenv("LOGGING_SERVICE_URL", "http://localhost:7000/")

class LoggingClient:
    """
    A client for sending logs to the LoggingService via RPC.
    Each service (ApiServer, Transcoder) will create its own instance
    of this class, which will manage its own local Lamport clock.
    """
    def __init__(self, service_name):
        self.service_name = service_name
        self.proxy = xmlrpc.client.ServerProxy(LOGGING_SERVICE_URL)
        
        # --- Client-side Lamport Clock ---
        self.local_clock = 0
        self.clock_lock = threading.Lock()
        
        self.log(f"{service_name} client initialized.")

    def log(self, message):
        """
        Sends a log message to the logging service.
        Implements the "send event" rule for Lamport clocks.
        """
        try:
            # --- Lamport Clock Logic ---
            # 1. Acquire lock
            with self.clock_lock:
                # 2. Increment local clock (a "send" event)
                self.local_clock += 1
                my_clock_time = self.local_clock
            
            # 3. Send the log with the current clock time
            self.proxy.log_message(self.service_name, message, my_clock_time)
        
        except (xmlrpc.client.Fault, ConnectionRefusedError) as e:
            # Don't crash the main app if the logging service is down
            print(f"[{time.strftime('%H:%M:%S')}] WARN: Could not send log to LoggingService. {e}")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] WARN: Unknown logging error. {e}")

    def get_clock(self):
        """Gets the current local clock value."""
        with self.clock_lock:
            return self.local_clock

    def update_clock(self, remote_clock):
        """Updates the local clock after receiving a message (e.g., an HTTP response)."""
        with self.clock_lock:
            self.local_clock = max(self.local_clock, remote_clock) + 1
            return self.local_clock