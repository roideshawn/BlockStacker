import os
import shutil
import json
import uuid

class SaveManager:
    """Handles the internal App Sandbox, file copying, and JSON persistence."""
    
    def __init__(self):
        self.base_dir = "userdata"
        self.img_dir = os.path.join(self.base_dir, "images")
        self.audio_dir = os.path.join(self.base_dir, "audio")
        self.save_file = os.path.join(self.base_dir, "save_data.json")

        self._ensure_directories()
        self.data = self._load_data()

    def _ensure_directories(self) -> None:
        """Creates the protected sandbox folders if they don't exist."""
        os.makedirs(self.img_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)

    def _load_data(self) -> dict:
        """Loads the user's custom themes from the JSON file."""
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not read save data: {e}")
        
        # If no save exists (first boot), return an empty template
        return {"custom_themes": []}

    def save_data(self) -> None:
        """Writes the current state to the JSON file."""
        try:
            with open(self.save_file, "w") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Warning: Could not write save data: {e}")

    def import_asset(self, source_path: str, asset_type: str) -> str:
        """Copies a file from the user's computer into the engine's sandbox."""
        if not source_path or not os.path.exists(source_path):
            return None

        # Determine destination folder
        target_dir = self.img_dir if asset_type == "image" else self.audio_dir
        
        # Extract the original file extension (e.g., '.png', '.wav')
        _, ext = os.path.splitext(source_path)
        
        # Generate a unique 8-character filename so we avoid overwrite collisions
        unique_filename = f"{uuid.uuid4().hex[:8]}{ext}"
        destination_path = os.path.join(target_dir, unique_filename)

        try:
            # Physically copy the file into our game's internal folder
            shutil.copy2(source_path, destination_path)
            
            # Convert to forward slashes for cross-platform compatibility in the JSON
            return destination_path.replace("\\", "/")
        except Exception as e:
            print(f"Error copying asset: {e}")
            return None

    def save_custom_theme(self, theme_data: dict) -> None:
        """Saves or updates a custom theme in the persistence file."""
        # Check if this theme name already exists and overwrite it if so
        for i, theme in enumerate(self.data["custom_themes"]):
            if theme.get("name") == theme_data.get("name"):
                self.data["custom_themes"][i] = theme_data
                self.save_data()
                return
        
        # Otherwise, append it as a brand new theme
        self.data["custom_themes"].append(theme_data)
        self.save_data()

    def get_custom_themes(self) -> list:
        """Retrieves the list of saved custom themes."""
        return self.data.get("custom_themes", [])