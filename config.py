import os
import pathlib
from dotenv import load_dotenv

# Obtener ruta absoluta al directorio del proyecto
BASE_DIR = pathlib.Path(__file__).parent.absolute()
ENV_PATH = BASE_DIR / "datos.env.txt"
EXCEL_PATH = BASE_DIR / "data" / "usuarios.xlsx"

# Cargar variables de entorno
print(f"Cargando configuración desde: {ENV_PATH}")
load_dotenv(dotenv_path=ENV_PATH)

# Ruta a la base de datos
DB_PATH = BASE_DIR / "tutoria_ugr.db"

# Configuración del bot
TOKEN = os.getenv("BOT_TOKEN", "TU_TOKEN_AQUI")
GRUPO_BOT_TOKEN = "tu_token_del_bot_para_grupos_aquí"

# Configuración de email
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# Mapping de áreas y carreras
AREA_CARRERAS = {
    "Ciencias": ["Biología", "Química", "Física", "Matemáticas", "Geología"],
    "Ciencias Sociales y Jurídicas": ["Derecho", "Economía", "Psicología", "Magisterio", "Trabajo Social"],
    "Ciencias de la Salud": ["Medicina", "Enfermería", "Farmacia", "Fisioterapia", "Odontología"],
    "Artes y Humanidades": ["Historia", "Filosofía", "Lenguas Modernas", "Traducción e Interpretación", "Historia del Arte"],
    "Ingeniería y Arquitectura": ["Ingeniería Informática", "Ingeniería de Telecomunicaciones", "Arquitectura", "Ingeniería Civil", "Ingeniería Eléctrica"],
}