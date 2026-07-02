# Agents package: intent, planning, research, validation, gap analysis
import os

from src.core.config import Config


def load_prompt(name: str, default: str) -> str:
    """Load a prompt template from prompts/<name>.txt, else use the default."""
    path = os.path.join(Config.PROMPTS_DIR, f"{name}.txt")
    try:
        with open(path, "r") as f:
            content = f.read().strip()
            if content:
                return content
    except OSError:
        pass
    return default
