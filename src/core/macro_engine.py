"""
Macro engine for Helldivers Numpad Macros
Handles keyboard hooking and macro execution
"""

import time
import winsound
import keyboard
from .stratagem_data import STRATAGEMS
from ..config.constants import KEYBIND_MAPPINGS


class MacroEngine:
    """Manages macro execution and keyboard hooks"""
    
    def __init__(self, get_slots_callback, get_settings_callback, map_direction_callback):
        """
        Initialize macro engine
        
        Args:
            get_slots_callback: Function that returns dict of slots
            get_settings_callback: Function that returns global settings dict
            map_direction_callback: Function that maps direction to key
        """
        self.get_slots = get_slots_callback
        self.get_settings = get_settings_callback
        self.map_direction = map_direction_callback
        self.hooks_active = False
    
    def enable(self):
        """Enable keyboard hooks for macro execution"""
        try:
            keyboard.unhook_all()
        except:
            pass
        keyboard.hook(self._keyboard_event_handler)
        self.hooks_active = True
    
    def disable(self):
        """Disable keyboard hooks"""
        try:
            keyboard.unhook_all()
        except:
            pass
        self.hooks_active = False
    
    def is_enabled(self):
        """Check if macro hooks are active"""
        return self.hooks_active
    
    def _keyboard_event_handler(self, event):
        """
        Handle keyboard events for macro execution
        
        Args:
            event: Keyboard event
            
        Returns:
            False to suppress the key, True to allow it
        """
        if event.event_type == keyboard.KEY_DOWN:
            slots = self.get_slots()
            slot = slots.get(str(event.scan_code))
            
            if slot and slot.assigned_stratagem:
                if getattr(event, 'is_keypad', True):
                    stratagem_name = slot.assigned_stratagem
                    seq = STRATAGEMS.get(stratagem_name)
                    if seq:
                        slot.run_macro(stratagem_name, seq, slot.label_text)
                    return False  # Suppress the keypad key
        
        return True  # Allow the key through
    
    @staticmethod
    def map_direction_to_key(direction, keybind_mode="arrows"):
        """
        Map stratagem direction to actual key based on user setting
        
        Args:
            direction: Direction string (up, down, left, right)
            keybind_mode: "arrows" or "wasd"
            
        Returns:
            Key string to press
        """
        mapping = KEYBIND_MAPPINGS.get(keybind_mode, KEYBIND_MAPPINGS["arrows"])
        return mapping.get(direction, direction)
