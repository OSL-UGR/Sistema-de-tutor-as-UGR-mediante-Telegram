import os
import pathlib
from dotenv import load_dotenv

# Obtener ruta absoluta al directorio del proyecto
BASE_DIR = pathlib.Path(__file__).parent.absolute()
ENV_PATH = BASE_DIR / "datos.env"

# Cargar variables de entorno
print(f"Cargando configuración desde: {ENV_PATH}")
load_dotenv(dotenv_path=ENV_PATH)

# Acceso a la base de datos
DB_USER = os.getenv("DB_USER", "TU_DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD", "TU_DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "TU_DB_HOST")
DB_NAME = os.getenv("DB_NAME", "TU_DB_NAME")

MOODLE_USER = os.getenv("MOODLE_USER", "MOODLE_USER")
MOODLE_PASSWORD = os.getenv("MOODLE_PASSWORD", "MOODLE_PASSWORD")
MOODLE_TOKEN = os.getenv("MOODLE_TOKEN", "MOODLE_TOKEN")
MOODLE_ADDRESS = os.getenv("MOODLE_ADDRESS", "MOODLE_ADDRESS")

# Configuración del bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "TU_TOKEN_AQUI")
BOT_TOKEN_GRUPO = os.getenv("BOT_TOKEN_GRUPO", "tu_token_del_bot_para_grupos_aquí")
BOT_GRUPO_NOMBRE = os.getenv("BOT_GRUPO_NOMBRE", "nombre_bot")

# Configuración de email
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")