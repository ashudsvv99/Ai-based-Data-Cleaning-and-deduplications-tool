import os
import re

def update_config_file(updates: dict):
    """
    Updates config.py with the provided dictionary of new values.
    Safely uses regex to replace the variable assignments while preserving comments.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(project_root, "config.py")
    
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    for key, value in updates.items():
        # Match pattern: KEY = VALUE  # Optional comment
        pattern = re.compile(rf"^({key}\s*=\s*)([^#\n\r]*)(.*)$", re.MULTILINE)
        
        if isinstance(value, str):
            if key == "LLM_BASE_URL":
                formatted_value = f'os.getenv("LM_STUDIO_URL", "{value}")'
            else:
                formatted_value = f'"{value}"'
        else:
            formatted_value = str(value)
            
        content = pattern.sub(lambda m: f"{m.group(1)}{formatted_value} {m.group(3)}", content)
            
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)
