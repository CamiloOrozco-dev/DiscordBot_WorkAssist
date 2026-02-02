"""
Configuraciones del bot
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de Discord
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Configuración de Jibble
JIBBLE_CLIENT_ID = os.getenv("JIBBLE_CLIENT_ID")
JIBBLE_CLIENT_SECRET = os.getenv("JIBBLE_CLIENT_SECRET")
JIBBLE_ORG_ID = os.getenv("JIBBLE_ORG_ID")
JIBBLE_PROJECT_ID = os.getenv("JIBBLE_PROJECT_ID")

# Archivo de mapeo de usuarios
USER_MAPPING_FILE = os.path.join(os.path.dirname(__file__), "..", "user_mapping.json")

# Configuración de Roles (Discord IDs)
ROLE_ACTIVE_ID = "1463582976150343761"
ROLE_BREAK_ID = "1463583082702438615"
ROLE_INACTIVE_ID = "1463998777055514746"

# Configuración de GitLab
GITLAB_WEBHOOK_PORT = int(os.getenv("GITLAB_WEBHOOK_PORT", 5000))
GITLAB_CHANNEL_ID = os.getenv("GITLAB_CHANNEL_ID")
GITLAB_WEBHOOK_SECRET = os.getenv("GITLAB_WEBHOOK_SECRET")

# Lista de proyectos permitidos (separados por coma en .env)
_allowed_projects_raw = os.getenv("GITLAB_ALLOWED_PROJECTS", "")
GITLAB_ALLOWED_PROJECTS = [p.strip() for p in _allowed_projects_raw.split(",") if p.strip()]