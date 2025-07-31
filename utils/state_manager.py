from collections import defaultdict
import time  # Añadir importación de time

INITIAL_STATE = "INICIO"

# Campos user_data usados
DIA_ACTUAL = "dia_actual"
TOKEN = "token"
TOKEN_EXPIRY = "token_expiry"
PROFESOR_ID = "profesor_id"
PROFESOR_NOMBRE = "profesor_nombre"
ESTUDIANTE_ID = "estudiante_id"
GRUPO_ID = "grupo_id"
PUNTUACION = "puntuacion"
MENSAJE_ID = "id_mensaje"
COMENTARIO = "comentario"
CHAT_ID = "chat_id"

# Estados de usuario y datos temporales (compartidos entre módulos)
user_states = defaultdict(dict)  # Usar defaultdict para evitar KeyError
user_data = defaultdict(dict)  # Usar defaultdict para evitar KeyError
estados_timestamp = {}  # Añadir esta variable

def get_state(chat_id):
    """Obtiene el estado actual del chat"""
    return user_states.get(chat_id, INITIAL_STATE)

def set_state(chat_id, state):
    """Establece el estado para un chat"""
    user_states[chat_id] = state
    estados_timestamp[chat_id] = time.time()  # Actualizar timestamp
    return state

def clear_state(chat_id):
    """Limpia el estado del usuario"""
    if chat_id in user_states:
        del user_states[chat_id]
    if chat_id in user_data:
        del user_data[chat_id]
    if chat_id in estados_timestamp:  # También limpiar el timestamp
        del estados_timestamp[chat_id]