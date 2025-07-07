"""
Utilidades y funciones auxiliares para el bot de grupos.
Estados, menús y funciones comunes.
"""
import time
import logging
from telebot import types

from utils.state_manager import estados_timestamp, clear_state

# Importar funciones de la base de datos compartidas
from db.queries import (get_usuarios)
from db.constantes import *

# Constantes
MAX_ESTADO_DURACION = 3600  # 1 hora en segundos

def configurar_logger():
    """Configura y devuelve el logger"""
    logger = logging.getLogger("bot_grupo")
    
    if not logger.handlers:
        handler = logging.FileHandler("logs/bot_grupos.log")
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)
    
    return logger

# Obtener logger
logger = configurar_logger()

# Funciones de interfaz de usuario
def menu_profesor():
    """Devuelve un teclado personalizado para profesores en un grupo"""
    # Crear un teclado personalizado con solo el botón de terminar tutoría
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    
    # Añadir solo el botón de terminar tutoría
    markup.add(
        types.KeyboardButton("❌ Terminar Tutoria")
    )
    
    return markup

def menu_estudiante():
    """Crea un teclado personalizado con solo el botón de finalizar tutoría"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("❌ Terminar Tutoria"))
    return markup

def configurar_comandos_por_rol():
    """Devuelve listas de comandos específicos para profesores y estudiantes."""
    # Comandos para profesores
    comandos_profesor = [
        types.BotCommand('/start', 'Iniciar el bot'),
        types.BotCommand('/configurar_grupo', 'Configuración inicial del grupo'),
        types.BotCommand('/help', 'Mostrar ayuda del bot'),
        types.BotCommand('/finalizar', 'Finalizar una sesión de tutoría'),
    ]
    
    # Comandos para estudiantes
    comandos_estudiante = [
        types.BotCommand('/start', 'Iniciar el bot'),
        types.BotCommand('/help', 'Mostrar ayuda del bot'),
        types.BotCommand('/finalizar', 'Finalizar una sesión de tutoría'),
    ]
    
    return (comandos_profesor, comandos_estudiante)

# Funciones de verificación y estado
def es_profesor(user_id):
    """Verifica si el usuario es un profesor"""
    user = get_usuarios(USUARIO_ID_TELEGRAM=user_id)
    return (user and user[0][USUARIO_TIPO] == USUARIO_TIPO_PROFESOR)

def limpiar_estados_obsoletos():
    """Limpia estados de usuario obsoletos para evitar fugas de memoria."""
    tiempo_actual = time.time()
    usuarios_para_limpiar = []
    
    # Identificar estados obsoletos
    for user_id, timestamp in estados_timestamp.items():
        if tiempo_actual - timestamp > MAX_ESTADO_DURACION:
            usuarios_para_limpiar.append(user_id)
    
    # Eliminar estados obsoletos
    for user_id in usuarios_para_limpiar:
        clear_state(user_id)
    
    if usuarios_para_limpiar:
        logger.info(f"Limpiados {len(usuarios_para_limpiar)} estados obsoletos")


def limpieza_periodica():
    while True:
        time.sleep(1800)  # 30 minutos
        try:
            limpiar_estados_obsoletos()
        except Exception as e:
            logger.error(f"Error en limpieza periódica: {e}")