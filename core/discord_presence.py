import time
import threading
from discordrp import Presence

class DiscordPresence:
    def __init__(self, client_id="1430908404095909960"):
        self.client_id = client_id
        self.presence = None
        self.running = False
        self.start_time = None
        self._thread = None
        self._stop_thread = threading.Event()

    def start(self):
        if self.running:
            print("Presence is already running")
            return
        
        self.running = True
        self._stop_thread.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("Discord presence manager started")

    def _run_loop(self):
        while not self._stop_thread.is_set():
            try:
                with Presence(self.client_id) as presence:
                    self.presence = presence
                    print("Successfully connected to Discord RPC.")
                    self.start_time = int(time.time())
                    self._set_initial_presence()

                    while not self._stop_thread.is_set():
                        time.sleep(15)
            
            except Exception as e:
                self.presence = None
                print(f"Failed to connect to Discord RPC: {e}. Retrying in 30 seconds...")
                
                for _ in range(30):
                    if self._stop_thread.is_set():
                        break
                    time.sleep(1)
        
        self.presence = None

    def _set_initial_presence(self):
        if not self.presence:
            return
        
        try:
            self.presence.set(
                {
                    "assets": {
                        "large_image": "2ktanbig",
                        "large_text": "CLARA"
                    },
                    "buttons": [
                        {
                            "label": "Let CLARA help you!",
                            "url": "https://github.com/n0va-bot/CLARA"
                        }
                    ]
                }
            )
        except Exception as e:
            print(f"Failed to set initial Discord presence: {e}")

    def end(self):
        if not self.running:
            print("Presence is not running")
            return

        print("Stopping Discord presence...")
        self._stop_thread.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        
        self.running = False
        self.presence = None
        print("Discord presence stopped")

    def update(self, data):
        if not self.running or not self.presence:
            return
        
        try:
            self.presence.set(data)
        except Exception as e:
            print(f"Failed to update Discord presence: {e}")

    def __del__(self):
        if self.running:
            self.end()


presence = DiscordPresence()