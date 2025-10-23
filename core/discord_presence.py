import time
from discordrp import Presence

class DiscordPresence:
    def __init__(self, client_id="1430908404095909960"):
        self.client_id = client_id
        self.presence = None
        self.running = False
        self.start_time = None
    
    def start(self):
        """Start the Discord Rich Presence"""
        if self.running:
            print("Presence is already running")
            return
        
        self.start_time = int(time.time())
        self.presence = Presence(self.client_id)
        self.presence.__enter__()
        
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
        
        self.running = True
        print("Discord presence started")
    
    def end(self):
        """Stop the Discord Rich Presence"""
        if not self.running:
            print("Presence is not running")
            return
        
        try:
            if self.presence:
                self.presence.__exit__(None, None, None)
                self.presence = None
        except Exception as e:
            print(f"Error closing presence: {e}")
        finally:
            self.running = False
            print("Discord presence stopped")
    
    def update(self, data):
        """Update the presence with new data"""
        if not self.running or not self.presence:
            print("Presence is not running. Call start() first.")
            return
        
        self.presence.set(data)
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        if self.running:
            self.end()


presence = DiscordPresence()