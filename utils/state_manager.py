import time  # Añadir importación de time

# Estados de usuario y datos temporales (compartidos entre módulos)
user_states = {}
user_data = {}
estados_timestamp = {}  # Añadir esta variable

def get_state(chat_id):
    """Obtiene el estado actual del chat"""
    return user_states.get(chat_id, 'INICIO')

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