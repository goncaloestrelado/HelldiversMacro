"""
Profile manager for Helldivers Numpad Macros
Handles loading, saving, and managing profiles
"""

import os
import json
from ..config.config import PROFILES_DIR, LEGACY_NAME_MAP


class ProfileManager:
    """Manages profile operations"""
    
    @staticmethod
    def get_profile_list():
        """Get list of available profiles"""
        if not os.path.exists(PROFILES_DIR):
            os.makedirs(PROFILES_DIR, exist_ok=True)
        files = [os.path.splitext(f)[0] for f in os.listdir(PROFILES_DIR) if f.endswith(".json")]
        return sorted(files)
    
    @staticmethod
    def load_profile(profile_name):
        """
        Load profile from file
        
        Args:
            profile_name: Name of the profile (without .json extension)
            
        Returns:
            dict with 'speed' and 'mappings' keys, or None if file doesn't exist
        """
        filepath = ProfileManager.get_profile_path(profile_name)
        if not os.path.exists(filepath):
            return None
        
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                
            mappings = data.get("mappings", {})
            migrated = False
            updated_mappings = {}
            
            for code, strat in mappings.items():
                if strat in LEGACY_NAME_MAP:
                    updated_mappings[code] = LEGACY_NAME_MAP[strat]
                    migrated = True
                else:
                    updated_mappings[code] = strat
            
            if migrated:
                data["mappings"] = updated_mappings
                ProfileManager.save_profile(profile_name, data)
            
            return data
        except Exception as e:
            print(f"[ProfileManager] Error loading profile: {e}")
            return None
    
    @staticmethod
    def save_profile(profile_name, data):
        """
        Save profile to file
        
        Args:
            profile_name: Name of the profile (without .json extension)
            data: dict with 'speed' and 'mappings' keys
        """
        filepath = ProfileManager.get_profile_path(profile_name)
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"[ProfileManager] Error saving profile: {e}")
            return False
    
    @staticmethod
    def delete_profile(profile_name):
        """Delete a profile file
        
        Args:
            profile_name: Name of the profile (without .json extension)
            
        Returns:
            True if deleted successfully, False otherwise
        """
        filepath = ProfileManager.get_profile_path(profile_name)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception as e:
            print(f"[ProfileManager] Error deleting profile: {e}")
            return False
    
    @staticmethod
    def profile_exists(profile_name):
        """Check if a profile exists
        
        Args:
            profile_name: Name of the profile (without .json extension)
            
        Returns:
            True if profile exists, False otherwise
        """
        filepath = ProfileManager.get_profile_path(profile_name)
        return os.path.exists(filepath)
    
    @staticmethod
    def get_profile_path(profile_name):
        """Get full path to a profile
        
        Args:
            profile_name: Profile name (without .json extension)
            
        Returns:
            Full path to profile file
        """
        # Remove .json extension if it was included
        if profile_name.endswith('.json'):
            profile_name = profile_name[:-5]
        return os.path.join(PROFILES_DIR, f"{profile_name}.json")
