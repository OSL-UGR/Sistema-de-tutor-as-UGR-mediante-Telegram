"""
Utilidades y funciones auxiliares para el bot de grupos.
Estados, menús y funciones comunes.
"""
import time
import logging
import sys
import os
from pathlib import Path
from telebot import types
import sqlite3
import threading

# Configurar paths para importaciones
root_path = str(Path(__file__).parent.parent.absolute())
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# Cargar state_manager usando importación dinámica para evitar problemas de rutas
import importlib.util
state_manager_path = Path(__file__).parent.parent / "utils" / "state_manager.py"
spec = importlib.util.spec_from_file_location("state_manager", state_manager_path)
state_manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state_manager)

# Obtener las variables de estado
user_states = state_manager.user_states
user_data = state_manager.user_data
estados_timestamp = state_manager.estados_timestamp

# Importar funciones de la base de datos compartidas
from db.queries import (
    get_user_by_telegram_id, 
    get_db_connection,
    create_user,
    crear_grupo_tutoria,
    añadir_estudiante_grupo
)

# Constantes
MAX_ESTADO_DURACION = 3600  # 1 hora en segundos

def configurar_logger():
    """Configura y devuelve el logger"""
    logger = logging.getLogger("bot_grupo")
    
    if not logger.handlers:
        handler = logging.FileHandler("bot_grupos.log")
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
        types.BotCommand('/ayuda', 'Mostrar ayuda del bot'),
        types.BotCommand('/estudiantes', 'Ver lista de estudiantes'),
        types.BotCommand('/estadisticas', 'Ver estadísticas de tutorías'),
        types.BotCommand('/finalizar', 'Finalizar una sesión de tutoría'),
        types.BotCommand('/cambiar_asignatura', 'Cambiar asignatura de una sala'),
        types.BotCommand('/eliminar_sala', 'Eliminar configuración de una sala')
    ]
    
    # Comandos para estudiantes
    comandos_estudiante = [
        types.BotCommand('/start', 'Iniciar el bot'),
        types.BotCommand('/ayuda', 'Mostrar ayuda del bot'),
        types.BotCommand('/finalizar', 'Finalizar una sesión de tutoría')
    ]
    
    return comandos_profesor, comandos_estudiante

# Funciones de verificación y estado
def es_profesor(user_id):
    """Verifica si el usuario es un profesor"""
    user = get_user_by_telegram_id(user_id)
    if user and user['Tipo'] == 'profesor':
        return True
    return False

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
        if user_id in user_states:
            logger.info(f"Limpiando estado obsoleto para usuario {user_id}")
            del user_states[user_id]
        if user_id in estados_timestamp:
            del estados_timestamp[user_id]
    
    if usuarios_para_limpiar:
        logger.info(f"Limpiados {len(usuarios_para_limpiar)} estados obsoletos")

# Funciones de base de datos
def inicializar_tablas_grupo():
    """Inicializa las tablas necesarias para grupos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Crear tabla Usuario_Grupo
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Usuario_Grupo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Id_usuario INTEGER,
            id_sala INTEGER,
            fecha_union TEXT,
            FOREIGN KEY (Id_usuario) REFERENCES Usuarios(Id_usuario),
            FOREIGN KEY (id_sala) REFERENCES Grupos_tutoria(id_sala),
            UNIQUE(Id_usuario, id_sala)
        )
    """)
    
    # Verificar columna chat_id en Grupos_tutoria
    cursor.execute("PRAGMA table_info(Grupos_tutoria)")
    columnas = [info[1] for info in cursor.fetchall()]
    if "chat_id" not in columnas:
        cursor.execute("ALTER TABLE Grupos_tutoria ADD COLUMN chat_id INTEGER")
        logger.info("Añadida columna 'chat_id' a Grupos_tutoria")
    
    conn.commit()
    conn.close()

def guardar_usuario_en_grupo(user_id, username, chat_id):
    """Guarda un usuario en un grupo específico"""
    try:
        # Verificar si el usuario ya existe
        user = get_user_by_telegram_id(user_id)
        
        if not user:
            # Si no existe, crearlo como estudiante usando la función existente
            user_id_db = create_user(
                nombre=username, 
                tipo='estudiante',
                email=None,
                telegram_id=user_id
            )
            logger.info(f"Nuevo usuario {username} (ID: {user_id}) creado")
        else:
            user_id_db = user['Id_usuario']
        
        # Asegurar estructura de tabla
        inicializar_tablas_grupo()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar grupo por chat_id 
        cursor.execute("SELECT id_sala FROM Grupos_tutoria WHERE chat_id = ?", (chat_id,))
        grupo = cursor.fetchone()
        conn.close()
        
        if not grupo:
            # Usar función existente para crear grupo
            grupo_id = crear_grupo_tutoria(
                profesor_id=1,  # Usar un ID válido
                nombre_sala=f"Grupo {chat_id}",
                tipo_sala="publica",
                chat_id=chat_id,
                enlace=f"https://t.me/c/{chat_id}"
            )
            logger.info(f"Nuevo grupo creado para chat_id {chat_id}")
        else:
            grupo_id = grupo[0]
        
        # Usar función existente para añadir al estudiante
        añadir_estudiante_grupo(grupo_id, user_id_db)
        
        logger.info(f"Usuario {username} (ID: {user_id}) asociado al grupo {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Error guardando usuario en grupo: {e}")
        return False

# Funciones de formateo de mensajes
def escape_markdown(text):
    """Escapa caracteres especiales de Markdown"""
    if not text:
        return ""
    # Caracteres especiales en Markdown V2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    return text

def send_markdown_message(bot, chat_id, text, reply_markup=None):
    """Envía un mensaje con Markdown escapando correctamente los caracteres especiales"""
    try:
        # Intentar enviar con Markdown
        return bot.send_message(
            chat_id,
            text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    except Exception as e:
        # Si falla, intentar sin formato
        logger.warning(f"Error al enviar mensaje con Markdown: {e}")
        return bot.send_message(
            chat_id,
            text,
            parse_mode=None,
            reply_markup=reply_markup
        )

# Un lock global para sincronizar acceso a la base de datos
db_lock = threading.RLock()

def execute_db_operation(operation_func, max_retries=5, retry_delay=0.5):
    """
    Ejecuta una operación de base de datos con reintentos y manejo de bloqueos.
    
    Args:
        operation_func: Función que recibe una conexión y cursor y realiza operaciones DB
        max_retries: Número máximo de intentos si hay bloqueo
        retry_delay: Tiempo de espera entre reintentos
    
    Returns:
        El resultado de operation_func o None si falla
    """
    from db.queries import get_db_connection
    
    retries = 0
    while retries < max_retries:
        conn = None
        try:
            # Adquirir lock para evitar competencia
            with db_lock:
                conn = get_db_connection()
                # Configurar timeout más largo para esperar que se libere el bloqueo
                conn.execute("PRAGMA busy_timeout = 5000")
                cursor = conn.cursor()
                
                # Ejecutar la operación proporcionada
                result = operation_func(conn, cursor)
                
                # Commit si todo salió bien
                conn.commit()
                return result
                
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                retries += 1
                logging.warning(f"Base de datos bloqueada, reintento {retries}/{max_retries}")
                time.sleep(retry_delay)
            else:
                logging.error(f"Error de base de datos: {e}")
                import traceback
                traceback.print_exc()
                return None
        except Exception as e:
            logging.error(f"Error ejecutando operación de BD: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            # Asegurar que siempre se cierra la conexión
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    # Si llegamos aquí, se agotaron los reintentos
    logging.error("Máximo de reintentos alcanzado para operación de BD")
    return None