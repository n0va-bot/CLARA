import json
from pathlib import Path
from typing import Any, Dict
import platform

class Config:
    DEFAULT_CONFIG = {
        "hotkey": "super",
        "discord_presence": True,
        "auto_update": True,
        "http_share_port": 8080,
        "dukto_udp_port": 4644,
        "dukto_tcp_port": 4644,
        "search_engine": "brave"
    }
    
    def __init__(self):
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self.config_data = self._load_config()
    
    def _get_config_dir(self) -> Path:
        system = platform.system()
        
        if system == "Windows":
            base = Path.home() / "AppData" / "Roaming"
        else:
            base = Path.home() / ".config"
        
        config_dir = base / "CLARA"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def _load_config(self) -> Dict[str, Any]:
        system = platform.system()

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with defaults for updates
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(loaded)
                    return config
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}. Using defaults.")
                return self.DEFAULT_CONFIG.copy()
        else:
            # default config file
            conf = self.DEFAULT_CONFIG.copy()
            if system == "Windows":
                conf["hotkey"] = "ctrl+space"
            else:
                conf["hotkey"] = "super"
            
            self._save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()
    
    def _save_config(self, config_data: Dict[str, Any]):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
        except IOError as e:
            print(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        return self.config_data.get(key, default)
    
    def set(self, key: str, value: Any):
        self.config_data[key] = value
        self._save_config(self.config_data)
    
    def get_all(self) -> Dict[str, Any]:
        return self.config_data.copy()
    
    def reset(self):
        self.config_data = self.DEFAULT_CONFIG.copy()
        self._save_config(self.config_data)


# Global config instance
config = Config()