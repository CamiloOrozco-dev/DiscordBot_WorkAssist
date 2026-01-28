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
ROLE_BREAK_ID = "1463998777055514746"
ROLE_INACTIVE_ID = "1463583082702438615"