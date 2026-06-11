"""Configuration management for the toolkit"""

import os
from pathlib import Path
from typing import Optional


def get_api_key(key_name: str) -> Optional[str]:
    """Get an API key from multiple sources in order of priority"""
    # 1. Environment variable
    api_key = os.getenv(key_name)
    if api_key:
        return api_key

    # 2. System-wide config file (~/.config/study-tk/config)
    config_dir = Path.home() / ".config" / "study-tk"
    config_file = config_dir / "config"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                for line in f:
                    if line.startswith(f"{key_name}="):
                        return line.split("=", 1)[1].strip()
        except Exception:
            pass

    # 3. Legacy .env file (for backward compatibility)
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv(key_name)
        if api_key:
            return api_key
    except ImportError:
        pass

    return None


def get_mistral_api_key() -> Optional[str]:
    """Get Mistral API key from multiple sources in order of priority"""
    return get_api_key("MISTRAL_API_KEY")



def save_api_key(key_name: str, api_key: str) -> bool:
    """Save an API key to config file"""
    config_dir = Path.home() / ".config" / "study-tk"
    config_file = config_dir / "config"

    try:
        # Create config directory
        config_dir.mkdir(parents=True, exist_ok=True)

        # Read existing config
        lines = []
        key_found = False
        if config_file.exists():
            with open(config_file, 'r') as f:
                for line in f:
                    if line.startswith(f"{key_name}="):
                        lines.append(f"{key_name}={api_key}\n")
                        key_found = True
                    else:
                        lines.append(line)

        if not key_found:
            lines.append(f"{key_name}={api_key}\n")

        # Save API key
        with open(config_file, 'w') as f:
            f.writelines(lines)

        # Set appropriate permissions (readable only by user)
        os.chmod(config_file, 0o600)
        return True
    except Exception:
        return False


def save_mistral_api_key(api_key: str) -> bool:
    """Save Mistral API key to config file"""
    return save_api_key("MISTRAL_API_KEY", api_key)


