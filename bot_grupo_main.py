"""
Archivo principal del bot de grupos de tutorías.
Inicialización, configuración y handlers básicos.
"""
import telebot
from telebot import types
import threading
import time
import os
import sys
import logging
import sqlite3
from dotenv import load_dotenv

# Importar utilidades y handlers
from grupo_handlers.grupos import GestionGrupos
from grupo_handlers.valoraciones import register_handlers as register_valoraciones_handlers
from grupo_handlers.usuarios import register_student_handlers
from grupo_handlers.utils import (
    limpiar_estados_obsoletos, es_profesor, menu_profesor, menu_estudiante, 
    configurar_logger, configurar_comandos_por_rol
)
# Importar estados desde el manejador central
from utils.state_manager import user_states, user_data, estados_timestamp, set_state, get_state, clear_state

# Configuración de logging
logger = configurar_logger()

# Cargar token del bot de grupos
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, "datos.env.txt")

if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    logger.info(f"Cargando variables desde {env_path}")
else:
    load_dotenv()
    logger.warning("No se encontró archivo de variables específico")

# Estandarizar el nombre del token
BOT_TOKEN = os.getenv("TOKEN_GRUPO")
if not BOT_TOKEN:
    logger.warning("TOKEN_GRUPO no encontrado, buscando TOKEN_1 como alternativa")
    BOT_TOKEN = os.getenv("TOKEN_1")
    
if not BOT_TOKEN:
    logger.critical("Token del bot de grupos no encontrado")
    print("El token del bot de grupos no está configurado. Añade TOKEN_GRUPO en datos.env.txt")
    sys.exit(1)

from telebot import apihelper
apihelper.ENABLE_MIDDLEWARE = True

# Inicializar el bot
bot = telebot.TeleBot(BOT_TOKEN)

# Establecer el nivel de logging de telebot a DEBUG
telebot.logger.setLevel(logging.DEBUG)

# Mecanismo para prevenir instancias duplicadas del bot
import socket
import sys
import atexit

def prevent_duplicate_instances(port=12345):
    """Evita que se ejecuten múltiples instancias del bot usando un socket de bloqueo"""
    global lock_socket
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        lock_socket.bind(('localhost', port))
        print(f"🔒 Instancia única asegurada en el puerto {port}")
    except socket.error:
        print("⚠️ ADVERTENCIA: Otra instancia del bot ya está en ejecución.")
        print("⚠️ Cierra todas las demás instancias antes de ejecutar este script.")
        sys.exit(1)

    # Asegurar que el socket se cierra al salir
    def cleanup():
        lock_socket.close()
    atexit.register(cleanup)

# Prevenir múltiples instancias
prevent_duplicate_instances()

# Crear una función wrapper que maneje errores de Markdown
def safe_send_message(chat_id, text, parse_mode=None, **kwargs):
    if parse_mode == "Markdown":
        try:
            return bot.send_message(chat_id, text, parse_mode=parse_mode, **kwargs)
        except Exception as e:
            logger.warning(f"Error con Markdown, reintentando sin formato: {e}")
            return bot.send_message(chat_id, text, parse_mode=None, **kwargs)
    else:
        return bot.send_message(chat_id, text, parse_mode=parse_mode, **kwargs)

# Importar funciones de la base de datos compartidas
from db.queries import get_db_connection, get_user_by_telegram_id, crear_grupo_tutoria

# Handlers básicos
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user = get_user_by_telegram_id(user_id)
    
    if not user:
        bot.send_message(
            chat_id,
            "👋 Bienvenido al sistema de tutorías en grupos.\n\n"
            "No te encuentro registrado en el sistema. Por favor, primero regístrate con el bot principal."
        )
        return
    
    # Actualizar interfaz según rol y tipo de chat
    if message.chat.type in ['group', 'supergroup']:
        # Estamos en un grupo
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Grupos_tutoria WHERE Chat_id = ?", (str(chat_id),))
        grupo = cursor.fetchone()
        conn.close()
        
        if grupo:
            # Es un grupo de tutoría registrado
            if user['Tipo'] == 'profesor':
                bot.send_message(
                    chat_id,
                    "👨‍🏫 *Bot de tutoría activo*\n\n"
                    "Este grupo está configurado como sala de tutoría. Usa los botones para gestionarla.",
                    reply_markup=menu_profesor(),
                    parse_mode="Markdown"
                )
            else:
                # Es estudiante
                bot.send_message(
                    chat_id,
                    "👨‍🎓 *Bot de tutoría activo*\n\n"
                    "Cuando termines tu consulta, usa el botón para finalizar la tutoría.",
                    reply_markup=menu_estudiante(),
                    parse_mode="Markdown"
                )
        else:
            # No es un grupo registrado
            if user['Tipo'] == 'profesor':
                bot.send_message(
                    chat_id,
                    "Este grupo no está configurado como sala de tutoría. Usa /configurar_grupo para configurarlo."
                )
    else:
        # Es un chat privado
        if user['Tipo'] == 'profesor':
            bot.send_message(
                chat_id,
                "¡Bienvenido, Profesor! Usa los botones para gestionar tus tutorías.",
                reply_markup=menu_profesor()
            )
        else:
            # Es estudiante
            bot.send_message(
                chat_id,
                "¡Hola! Para unirte a una tutoría, necesitas el enlace de invitación de tu profesor.",
                reply_markup=menu_estudiante()
            )
    
    logger.info(f"Usuario {user_id} ({user['Nombre']}) ha iniciado el bot en chat {chat_id}")
    actualizar_interfaz_usuario(user_id, chat_id)

@bot.message_handler(commands=['ayuda'])
def ayuda_comando(message):
    chat_id = message.chat.id
    bot.send_message(
        chat_id,
        "ℹ️ *Ayuda del Bot*\n\n"
        "🔹 Usa los siguientes comandos para interactuar con el bot:\n"
        "✅ /ayuda - Muestra este mensaje de ayuda.\n"
        "✅ Pulsa el botón '❌ Terminar Tutoria' para finalizar tu consulta o expulsar a un estudiante (solo para profesores).\n"
        "✅ /start - Almacena tus datos y te da la bienvenida si eres estudiante.",
        parse_mode="Markdown"
    )
    logger.info(f"Mensaje de ayuda enviado a {chat_id}")

def actualizar_interfaz_usuario(user_id, chat_id=None):
    """Actualiza la interfaz completa según el rol del usuario."""
    comandos_profesor, comandos_estudiante = configurar_comandos_por_rol()
    try:
        if es_profesor(user_id):
            # Actualizar comandos visibles
            scope = telebot.types.BotCommandScopeChat(user_id)
            bot.set_my_commands(comandos_profesor, scope)
            
            # Si hay un chat_id, enviar menú de profesor
            if chat_id:
                bot.send_message(
                    chat_id,
                    "🔄 Interfaz actualizada para profesor",
                    reply_markup=menu_profesor()
                )
            logger.info(f"Interfaz de profesor configurada para usuario {user_id}")
        else:
            # Actualizar comandos visibles
            scope = telebot.types.BotCommandScopeChat(user_id)
            bot.set_my_commands(comandos_estudiante, scope)
            
            # Si hay un chat_id, enviar menú de estudiante
            if chat_id:
                bot.send_message(
                    chat_id,
                    "🔄 Interfaz actualizada para estudiante",
                    reply_markup=menu_estudiante()
                )
            logger.info(f"Interfaz de estudiante configurada para usuario {user_id}")
    except Exception as e:
        logger.error(f"Error configurando interfaz para usuario {user_id}: {e}")

# Iniciar hilo de limpieza periódica
def limpieza_periodica():
    while True:
        time.sleep(1800)  # 30 minutos
        try:
            limpiar_estados_obsoletos()
        except Exception as e:
            logger.error(f"Error en limpieza periódica: {e}")

# Reemplazar la función configurar_grupo actual con esta versión mejorada:
@bot.message_handler(commands=['configurar_grupo'])
def configurar_grupo(message):
    """
    Inicia el proceso de configuración de un grupo como sala de tutoría
    """
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Verificar que estamos en un grupo
    if message.chat.type not in ['group', 'supergroup']:
        bot.send_message(chat_id, "⚠️ Este comando solo funciona en grupos.")
        return

    # Verificar que el usuario es profesor
    if not es_profesor(user_id):
        bot.send_message(chat_id, "⚠️ Solo los profesores pueden configurar grupos.")
        return

    # Verificar que el bot tiene permisos de administrador
    bot_member = bot.get_chat_member(chat_id, bot.get_me().id)
    if bot_member.status != 'administrator':
        bot.send_message(
            chat_id,
            "⚠️ Para configurar este grupo necesito ser administrador con permisos para:\n"
            "- Invitar usuarios mediante enlaces\n"
            "- Eliminar mensajes\n"
            "- Restringir usuarios"
        )
        return

    # Verificar si el grupo ya está configurado
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Grupos_tutoria WHERE Chat_id = ?", (str(chat_id),))
    grupo = cursor.fetchone()

    if grupo:
        bot.send_message(chat_id, "ℹ️ Este grupo ya está configurado como sala de tutoría.")
        conn.close()
        return

    # Obtener ID del usuario profesor
    cursor.execute("SELECT Id_usuario FROM Usuarios WHERE TelegramID = ? AND Tipo = 'profesor'", (str(user_id),))
    profesor_row = cursor.fetchone()

    if not profesor_row:
        bot.send_message(chat_id, "⚠️ Solo los profesores registrados pueden configurar grupos.")
        conn.close()
        return

    profesor_id = profesor_row['Id_usuario']

    # CONSULTA MEJORADA: Obtener SOLO asignaturas sin sala de avisos asociada
    cursor.execute("""
        SELECT a.Id_asignatura, a.Nombre 
        FROM Asignaturas a 
        JOIN Matriculas m ON a.Id_asignatura = m.Id_asignatura
        WHERE m.Id_usuario = ? 
        AND NOT EXISTS (
            SELECT 1 
            FROM Grupos_tutoria g 
            WHERE g.Id_asignatura = a.Id_asignatura 
            AND g.Id_usuario = ?
        )
    """, (profesor_id, profesor_id))

    asignaturas_disponibles = cursor.fetchall()

    # Verificar si ya tiene sala de tutoría privada
    cursor.execute("""
        SELECT COUNT(*) as total
        FROM Grupos_tutoria g
        WHERE g.Id_usuario = ? AND g.Tipo_sala = 'privada'
    """, (profesor_id,))

    tiene_privada = cursor.fetchone()['total'] > 0

    # Depuración - Mostrar salas actuales
    cursor.execute("""
        SELECT g.id_sala, g.Nombre_sala, g.Id_asignatura, a.Nombre as Asignatura
        FROM Grupos_tutoria g
        LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
        WHERE g.Id_usuario = ?
    """, (profesor_id,))

    salas_actuales = cursor.fetchall()
    print(f"\n--- SALAS ACTUALES PARA PROFESOR ID {profesor_id} ---")
    for sala in salas_actuales:
        # Usar operador ternario para manejar valores nulos
        nombre_asignatura = sala['Asignatura'] if sala['Asignatura'] is not None else 'N/A'
        print(f"Sala ID: {sala['id_sala']}, Nombre: {sala['Nombre_sala']}, " + 
              f"Asignatura ID: {sala['Id_asignatura']}, Asignatura: {nombre_asignatura}")
    print("--- FIN SALAS ACTUALES ---\n")

    conn.close()

    # Verificar si hay asignaturas disponibles
    if not asignaturas_disponibles and not (not tiene_privada):
        mensaje = "⚠️ No hay más asignaturas disponibles para configurar."
        if tiene_privada:
            mensaje += "\n\nYa tienes una sala configurada para cada asignatura y una sala de tutoría privada."
        bot.send_message(chat_id, mensaje)
        return

    # Crear teclado con las asignaturas disponibles que no tienen sala
    markup = types.InlineKeyboardMarkup()

    if asignaturas_disponibles:
        for asig in asignaturas_disponibles:
            callback_data = f"config_asig_{asig[0]}"
            markup.add(types.InlineKeyboardButton(text=asig[1], callback_data=callback_data))

    # Añadir opción de tutoría privada SOLO si no tiene una ya
    if not tiene_privada:
        markup.add(types.InlineKeyboardButton("Tutoría Privada", callback_data="config_tutoria_privada"))
        print(f"✅ Usuario {user_id} NO tiene sala privada - Mostrando opción")
    else:
        print(f"⚠️ Usuario {user_id} YA tiene sala privada - Ocultando opción")

    # Comprobar si no hay opciones disponibles
    if not asignaturas_disponibles and tiene_privada:
        bot.send_message(
            chat_id,
            "⚠️ No puedes configurar más salas. Ya tienes una sala para cada asignatura y una sala privada."
        )
        return

    # Guardar estado para manejar la siguiente interacción
    set_state(user_id, "esperando_asignatura_grupo")
    user_data[user_id] = {"chat_id": chat_id}

    # Enviar mensaje con las opciones
    mensaje = "🏫 *Configuración de sala de tutoría*\n\n"

    if asignaturas_disponibles:
        mensaje += "Selecciona la asignatura para la que deseas configurar este grupo:"
    else:
        mensaje += "Ya has configurado salas para todas tus asignaturas."

    # Si ya tiene sala privada, informarle
    if tiene_privada:
        mensaje += "\n\n*Nota:* Ya tienes una sala de tutoría privada configurada, por lo que esa opción no está disponible."

    bot.send_message(
        chat_id,
        mensaje,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('config_asig_'))
def handle_configuracion_asignatura(call):
    user_id = call.from_user.id
    id_asignatura = call.data.split('_')[2]  # Extraer ID de la asignatura

    # Verificar estado
    if get_state(user_id) != "esperando_asignatura_grupo":
        bot.answer_callback_query(call.id, "Esta opción ya no está disponible")
        return

    # Obtener datos guardados
    if user_id not in user_data or "chat_id" not in user_data[user_id]:
        bot.answer_callback_query(call.id, "Error: Datos no encontrados")
        clear_state(user_id)
        return

    chat_id = user_data[user_id]["chat_id"]

    try:
        # Registrar el grupo en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener nombre de la asignatura
        cursor.execute("SELECT Nombre FROM Asignaturas WHERE Id_asignatura = ?", (id_asignatura,))
        asignatura_nombre = cursor.fetchone()[0]

        # Obtener Id_usuario del profesor a partir de su TelegramID
        cursor.execute("SELECT Id_usuario FROM Usuarios WHERE TelegramID = ?", (str(user_id),))
        id_usuario_profesor = cursor.fetchone()[0]

        # Cerrar la conexión temporal
        conn.close()

        # Crear enlace de invitación si es posible
        try:
            enlace_invitacion = bot.create_chat_invite_link(chat_id).invite_link
        except:
            enlace_invitacion = None

        # Configurar directamente como sala de avisos (pública)
        # CORRECCIÓN: Usar "pública" con tilde para cumplir con el constraint
        tipo_sala = "pública"  # Cambiado de "publica" a "pública"
        sala_tipo_texto = "Avisos"
        nuevo_nombre = f"{asignatura_nombre} - Avisos"

        # Cambiar el nombre del grupo
        try:
            bot.set_chat_title(chat_id, nuevo_nombre)
        except Exception as e:
            logger.warning(f"No se pudo cambiar el nombre del grupo: {e}")

        # Crear el grupo en la base de datos
        from db.queries import crear_grupo_tutoria
        crear_grupo_tutoria(
            profesor_id=id_usuario_profesor,
            nombre_sala=nuevo_nombre,
            tipo_sala=tipo_sala,  # Ahora con el valor correcto "pública"
            asignatura_id=id_asignatura,
            chat_id=str(chat_id),
            enlace=enlace_invitacion
        )

        # Mensaje de éxito
        bot.edit_message_text(
            f"✅ Grupo configurado exitosamente como sala de avisos para *{asignatura_nombre}*",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="Markdown"
        )

        # Enviar mensaje informativo
        descripcion = "Esta es una sala para **avisos generales** de la asignatura donde los estudiantes pueden unirse mediante el enlace de invitación."

        bot.send_message(
            chat_id,
            f"🎓 *Sala configurada*\n\n"
            f"Esta sala está ahora configurada como: *Sala de Avisos*\n\n"
            f"{descripcion}\n\n"
            "Como profesor puedes:\n"
            "• Gestionar el grupo según el propósito configurado\n"
            "• Compartir el enlace de invitación con tus estudiantes",
            parse_mode="Markdown",
            reply_markup=menu_profesor()  # Esto ahora devuelve un ReplyKeyboardMarkup
        )

    except Exception as e:
        bot.send_message(chat_id, f"❌ Error al configurar grupo: {str(e)}")
        logger.error(f"Error en la selección de asignatura {chat_id}: {e}")

    # Limpiar estado
    clear_state(user_id)

@bot.callback_query_handler(func=lambda call: call.data == 'config_tutoria_privada')
def handle_configuracion_tutoria_privada(call):
    user_id = call.from_user.id
    
    # Verificar estado
    if get_state(user_id) != "esperando_asignatura_grupo":
        bot.answer_callback_query(call.id, "Esta opción ya no está disponible")
        return
        
    # Obtener datos guardados
    if user_id not in user_data or "chat_id" not in user_data[user_id]:
        bot.answer_callback_query(call.id, "Error: Datos no encontrados")
        clear_state(user_id)
        return
        
    chat_id = user_data[user_id]["chat_id"]
    
    try:
        # Registrar el grupo en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener Id_usuario y nombre del profesor a partir de su TelegramID
        cursor.execute("SELECT Id_usuario, Nombre FROM Usuarios WHERE TelegramID = ?", (str(user_id),))
        profesor = cursor.fetchone()
        id_usuario_profesor = profesor[0]
        nombre_profesor = profesor[1]

        # Cerrar la conexión temporal
        conn.close()

        # Crear enlace de invitación si es posible
        try:
            enlace_invitacion = bot.create_chat_invite_link(chat_id).invite_link
        except:
            enlace_invitacion = None
        
        # Configurar como sala de tutorías privadas
        tipo_sala = "privada"
        sala_tipo_texto = "Tutoría Privada"
        nuevo_nombre = f"Tutoría Privada - Prof. {nombre_profesor}"
        
        # Cambiar el nombre del grupo
        try:
            bot.set_chat_title(chat_id, nuevo_nombre)
        except Exception as e:
            logger.warning(f"No se pudo cambiar el nombre del grupo: {e}")
        
        # Crear el grupo en la base de datos
        from db.queries import crear_grupo_tutoria
        crear_grupo_tutoria(
            profesor_id=id_usuario_profesor,
            nombre_sala=nuevo_nombre,
            tipo_sala=tipo_sala,
            asignatura_id="0",  # 0 indica que no está vinculado a una asignatura específica
            chat_id=str(chat_id),
            enlace=enlace_invitacion
        )
        
        # Mensaje de éxito
        bot.edit_message_text(
            f"✅ Grupo configurado exitosamente como sala de tutorías privadas",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="Markdown"
        )
        
        # Enviar mensaje informativo
        descripcion = "Esta es tu sala de **tutorías privadas** donde solo pueden entrar estudiantes que invites específicamente."
        
        bot.send_message(
            chat_id,
            f"🎓 *Sala configurada*\n\n"
            f"Esta sala está ahora configurada como: *Sala de Tutorías Privadas*\n\n"
            f"{descripcion}\n\n"
            "Como profesor puedes:\n"
            "• Invitar a estudiantes específicos para tutorías\n"
            "• Expulsar estudiantes cuando finalice la consulta",
            parse_mode="Markdown",
            reply_markup=menu_profesor()
        )
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error al configurar grupo: {str(e)}")
        logger.error(f"Error en la configuración de tutoría privada {chat_id}: {e}")
    
    # Limpiar estado
    clear_state(user_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('proposito_'))
def handle_proposito_sala(call):
    user_id = call.from_user.id
    
    # Verificar estado
    if get_state(user_id) != "esperando_proposito_sala":
        bot.answer_callback_query(call.id, "Esta opción ya no está disponible")
        return
    
    # Extraer información
    proposito = call.data.split('_')[1]  # avisos o tutoria
    
    # Obtener datos guardados
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "Error: Datos no encontrados")
        clear_state(user_id)
        return
    
    data = user_data[user_id]
    chat_id = data["chat_id"]
    asignatura_nombre = data["asignatura_nombre"]
    asignatura_id = data["asignatura_id"]
    enlace_invitacion = data["enlace_invitacion"]
    id_usuario_profesor = data["id_usuario_profesor"]
    
    try:
        if proposito == "avisos":
            # Es una sala de avisos para la asignatura (pública)
            id_asignatura = call.data.split('_')[2]
            tipo_sala = "pública"  # Cambiado de "publica" a "pública"
            sala_tipo_texto = "Avisos"
            nuevo_nombre = f"{asignatura_nombre} - Avisos"
            
            descripcion = "Esta es una sala para **avisos generales** de la asignatura donde los estudiantes pueden unirse mediante el enlace de invitación."
            
        else:
            # Es una sala de tutorías privada (independiente de asignaturas)
            tipo_sala = "privada"
            sala_tipo_texto = "Tutoría Privada"
            nuevo_nombre = f"Tutoría Privada - Prof. {data['id_usuario_profesor']}"
            asignatura_id = "0"  # Indicando que no está vinculada a una asignatura específica
            
            descripcion = "Esta es tu sala de **tutorías privadas** donde solo pueden entrar estudiantes que invites específicamente."
        
        # Cambiar nombre del grupo
        try:
            bot.set_chat_title(chat_id, nuevo_nombre)
        except Exception as e:
            logger.warning(f"No se pudo cambiar el nombre del grupo: {e}")
        
        # Crear el grupo en la base de datos
        from db.queries import crear_grupo_tutoria
        crear_grupo_tutoria(
            profesor_id=id_usuario_profesor,
            nombre_sala=nuevo_nombre,
            tipo_sala=tipo_sala,
            asignatura_id=asignatura_id,
            chat_id=str(chat_id),
            enlace=enlace_invitacion
        )
        
        # Mensaje de éxito
        bot.edit_message_text(
            f"✅ Grupo configurado exitosamente como sala de {sala_tipo_texto.lower()}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="Markdown"
        )
        
        # Enviar mensaje informativo
        bot.send_message(
            chat_id,
            f"🎓 *Sala configurada*\n\n"
            f"Esta sala está ahora configurada como: *{sala_tipo_texto}*\n\n"
            f"{descripcion}\n\n"
            "Como profesor puedes:\n"
            "• Gestionar el grupo según el propósito configurado\n"
            "• Eliminar alumnos cuando finalice la consulta",
            parse_mode="Markdown",
            reply_markup=menu_profesor()  # Esto ahora devuelve un ReplyKeyboardMarkup
        )
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error al configurar grupo: {str(e)}")
        logger.error(f"Error configurando grupo {chat_id}: {e}")
    
    # Limpiar estado
    clear_state(user_id)    
@bot.message_handler(func=lambda message: message.text == "👨‍🎓 Ver estudiantes")
def handle_ver_estudiantes_cmd(message):
    """Maneja el comando de ver estudiantes desde el teclado personalizado"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # Verificar que el usuario es profesor
    user = get_user_by_telegram_id(user_id)
    if not user or user['Tipo'] != 'profesor':
        bot.send_message(chat_id, "⚠️ Solo los profesores pueden ver la lista de estudiantes")
        return
        
    # Aquí va el código para mostrar la lista de estudiantes
    # (el mismo que tenías en tu handler de callback)
    try:
        # Obtener grupo y estudiantes
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que este chat es un grupo registrado
        cursor.execute(
            "SELECT id_sala FROM Grupos_tutoria WHERE Chat_id = ?", 
            (str(chat_id),)
        )
        sala = cursor.fetchone()
        
        if not sala:
            bot.send_message(chat_id, "⚠️ Este grupo no está configurado como sala de tutoría")
            conn.close()
            return
            
        sala_id = sala['id_sala']
        
        # Obtener lista de estudiantes
        cursor.execute("""
            SELECT u.Nombre, u.Apellidos, u.TelegramID, m.Fecha_incorporacion, m.Estado
            FROM Miembros_Grupo m
            JOIN Usuarios u ON m.Id_usuario = u.Id_usuario
            WHERE m.id_sala = ? AND u.Tipo = 'alumno'
            ORDER BY m.Fecha_incorporacion DESC
        """, (sala_id,))
        
        estudiantes = cursor.fetchall()
        conn.close()
        
        if not estudiantes:
            bot.send_message(
                chat_id, 
                "📊 *No hay estudiantes*\n\nAún no hay estudiantes en este grupo.",
                parse_mode="Markdown"
            )
            return
            
        # Crear mensaje con lista de estudiantes
        mensaje = "👨‍🎓 *Lista de estudiantes*\n\n"
        
        for i, est in enumerate(estudiantes, 1):
            nombre_completo = f"{est['Nombre']} {est['Apellidos'] or ''}"
            fecha = est['Fecha_incorporacion'].split()[0]  # Solo la fecha, no la hora
            estado = "✅ Activo" if est['Estado'] == 'activo' else "❌ Inactivo"
            
            mensaje += f"{i}. *{nombre_completo}*\n"
            mensaje += f"   • Desde: {fecha}\n"
            mensaje += f"   • Estado: {estado}\n\n"
        
        bot.send_message(chat_id, mensaje, parse_mode="Markdown")
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error al recuperar estudiantes: {str(e)}")
        logger.error(f"Error recuperando estudiantes del grupo {chat_id}: {e}")

@bot.message_handler(func=lambda message: message.text == "❌ Terminar Tutoria")
def handle_terminar_tutoria(message):
    """Maneja la acción de terminar tutoría según el rol del usuario"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    print(f"\n==================================================")
    print(f"⚠️⚠️⚠️ BOTÓN TERMINAR TUTORÍA PRESIONADO ⚠️⚠️⚠️")
    print(f"⚠️ Chat ID: {chat_id} | User ID: {user_id}")
    print(f"⚠️ Usuario: {message.from_user.first_name}")
    print("==================================================\n")
    
    try:
        # Verificar que estamos en una sala de tutoría
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Grupos_tutoria WHERE Chat_id = ?", (str(chat_id),))
        grupo = cursor.fetchone()
        
        if not grupo:
            bot.send_message(chat_id, "Esta función solo está disponible en salas de tutoría.")
            conn.close()
            return
        
        # Verificar el rol del usuario
        user = get_user_by_telegram_id(user_id)
        
        if not user:
            bot.send_message(chat_id, "No estás registrado en el sistema.")
            conn.close()
            return
        
        conn.close()
        
        # Comportamiento diferente según el rol
        if user['Tipo'] == 'profesor':
            # Es profesor: mostrar lista de alumnos para expulsar
            print(f"👨‍🏫 {user_id} ES PROFESOR - Mostrando lista de estudiantes")
            
            # Crear lista de estudiantes para seleccionar
            markup = types.InlineKeyboardMarkup(row_width=1)
            
            # Obtener miembros del grupo que no son administradores
            try:
                chat_admins = bot.get_chat_administrators(chat_id)
                admin_ids = [admin.user.id for admin in chat_admins]
                
                # Obtener todos los miembros
                chat_members = []
                offset = 0
                limit = 50  # Límite por consulta
                
                while True:
                    members_chunk = bot.get_chat_members(chat_id, offset=offset, limit=limit)
                    if not members_chunk:
                        break
                    chat_members.extend(members_chunk)
                    offset += limit
                    if len(members_chunk) < limit:
                        break
                
                # Filtrar estudiantes (no administradores)
                estudiantes = [m for m in chat_members if m.user.id not in admin_ids]
                
                if not estudiantes:
                    bot.send_message(chat_id, "No hay estudiantes en este grupo para finalizar sesión.")
                    return
                
                # Crear botones para cada estudiante
                for estudiante in estudiantes:
                    nombre = estudiante.user.first_name
                    if estudiante.user.last_name:
                        nombre += f" {estudiante.user.last_name}"
                    markup.add(
                        types.InlineKeyboardButton(
                            nombre, 
                            callback_data=f"terminar_{estudiante.user.id}"
                        )
                    )
                
                # Añadir botón de cancelar
                markup.add(types.InlineKeyboardButton("Cancelar", callback_data="cancelar_terminar"))
                
                # Enviar mensaje con la lista
                bot.send_message(
                    chat_id,
                    "Selecciona el estudiante cuya sesión deseas finalizar:",
                    reply_markup=markup
                )
            
            except Exception as e:
                print(f"❌ Error al obtener miembros del grupo: {e}")
                bot.send_message(
                    chat_id,
                    "No pude obtener la lista de estudiantes. Asegúrate de que tengo permisos de administrador."
                )
        
        else:
            # Es estudiante: auto-expulsión
            print(f"🎓 {user_id} ES ESTUDIANTE - Ejecutando auto-expulsión")
            
            try:
                # Obtener el nombre del estudiante
                nombre = message.from_user.first_name
                if message.from_user.last_name:
                    nombre += f" {message.from_user.last_name}"
                
                # Informar en el grupo antes de expulsar
                bot.send_message(
                    chat_id,
                    f"👋 {nombre} ha finalizado su sesión de tutoría."
                )
                
                # Expulsar al usuario (ban temporal de 30 segundos)
                until_date = int(time.time()) + 30
                bot.ban_chat_member(chat_id, user_id, until_date=until_date)
                
                # Enviar mensaje privado al estudiante
                try:
                    bot.send_message(
                        user_id,
                        "Has finalizado tu sesión de tutoría. ¡Gracias por participar!"
                    )
                except Exception as dm_error:
                    print(f"No se pudo enviar mensaje privado al usuario: {dm_error}")
                
            except Exception as e:
                print(f"❌ Error en auto-expulsión: {e}")
                bot.send_message(
                    chat_id,
                    "No pude procesar tu solicitud. Asegúrate de que el bot sea administrador con permisos suficientes."
                )
    
    except Exception as e:
        print(f"❌❌❌ ERROR EN HANDLER TERMINAR TUTORÍA: {e}")
        bot.send_message(chat_id, "Ocurrió un error al procesar tu solicitud.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("terminar_") or call.data == "cancelar_terminar")
def handle_terminar_estudiante(call):
    """Procesa la selección del profesor para terminar la sesión de un estudiante"""
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    
    print(f"\n==================================================")
    print(f"⚠️⚠️⚠️ CALLBACK TERMINAR ESTUDIANTE ⚠️⚠️⚠️")
    print(f"⚠️ Chat ID: {chat_id} | User ID: {user_id}")
    print(f"⚠️ Callback data: {call.data}")
    print("==================================================\n")
    
    try:
        # Verificar que es profesor
        user = get_user_by_telegram_id(user_id)
        if not user or user['Tipo'] != 'profesor':
            bot.answer_callback_query(call.id, "Solo los profesores pueden usar esta función.")
            return
        
        # Cancelar operación si se solicita
        if call.data == "cancelar_terminar":
            bot.edit_message_text(
                "Operación cancelada.",
                chat_id=chat_id,
                message_id=message_id
            )
            bot.answer_callback_query(call.id)
            return
        
        # Obtener ID del estudiante a expulsar
        estudiante_id = int(call.data.split("_")[1])
        
        try:
            # Obtener información del estudiante
            estudiante_info = bot.get_chat_member(chat_id, estudiante_id)
            nombre = estudiante_info.user.first_name
            if estudiante_info.user.last_name:
                nombre += f" {estudiante_info.user.last_name}"
            
            # Informar al grupo
            bot.send_message(
                chat_id,
                f"👋 El profesor ha finalizado la sesión de tutoría con {nombre}."
            )
            
            # Expulsar al estudiante (ban temporal de 30 segundos)
            until_date = int(time.time()) + 30
            bot.ban_chat_member(chat_id, estudiante_id, until_date=until_date)
            
            # Enviar mensaje privado al estudiante
            try:
                bot.send_message(
                    estudiante_id,
                    "El profesor ha finalizado tu sesión de tutoría. ¡Gracias por participar!"
                )
            except Exception as dm_error:
                print(f"No se pudo enviar mensaje privado al estudiante: {dm_error}")
            
            # Confirmar al profesor
            bot.edit_message_text(
                f"✅ Has finalizado la sesión de tutoría con {nombre}.",
                chat_id=chat_id,
                message_id=message_id
            )
            
        except Exception as e:
            print(f"❌ Error al expulsar estudiante: {e}")
            bot.edit_message_text(
                "No pude finalizar la sesión del estudiante. Asegúrate de que tengo permisos de administrador.",
                chat_id=chat_id,
                message_id=message_id
            )
    
    except Exception as e:
        print(f"❌❌❌ ERROR EN CALLBACK TERMINAR ESTUDIANTE: {e}")
        bot.answer_callback_query(call.id, "Ocurrió un error al procesar tu solicitud.")

# Handler para cuando un grupo es creado
@bot.message_handler(content_types=['group_chat_created'])
def handle_group_creation(message):
    """Responde cuando se crea un nuevo grupo"""
    chat_id = message.chat.id
    
    print("\n==================================================")
    print(f"🆕🆕🆕 NUEVO GRUPO CREADO: {chat_id} 🆕🆕🆕")
    print(f"🆕 Creado por: {message.from_user.first_name} (ID: {message.from_user.id})")
    print("==================================================\n")
    
    bot.send_message(
        chat_id,
        "¡Gracias por crear un grupo con este bot!\n\n"
        "Para poder configurar correctamente el grupo necesito ser administrador. "
        "Por favor, sigue estos pasos:\n\n"
        "1. Entra en la información del grupo\n"
        "2. Selecciona 'Administradores'\n"
        "3. Añádeme como administrador\n\n"
        "Una vez me hayas hecho administrador, usa el comando /configurar_grupo."
    )



# Registrar handlers externos
if __name__ == "__main__":
    print("\n==================================================")
    print("🚀🚀🚀 INICIANDO BOT DE GRUPOS Y TUTORÍAS 🚀🚀🚀")
    print("==================================================\n")
    
    # Eliminar cualquier webhook existente
    bot.remove_webhook()
    
    # Iniciar el hilo de limpieza periódica
    limpieza_thread = threading.Thread(target=limpieza_periodica)
    limpieza_thread.daemon = True
    limpieza_thread.start()
    
    try:
        # Registrar handlers de usuarios primero para darle prioridad
        from grupo_handlers.usuarios import register_student_handlers
        register_student_handlers(bot)
        print("✅ Handler de nuevos estudiantes registrado")
        
        # NO registres más handlers para new_chat_members aquí
        
        # Resto del código...
        gestion_grupos = GestionGrupos(db_path="db/tutoria.db")
        gestion_grupos.registrar_handlers(bot)
        print("✅ Handlers de gestión de grupos registrados")
        
        register_valoraciones_handlers(bot)
        print("✅ Handlers de valoraciones registrados")
        
        print("🤖 Bot iniciando polling...")
        
        # Usar polling con configuración mejorada
        bot.polling(
            none_stop=True, 
            interval=0, 
            timeout=60,
            allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"]  # Asegúrate de incluir chat_member
        )
        
    except Exception as e:
        logger.critical(f"Error crítico al iniciar el bot: {e}")
        print(f"❌ ERROR CRÍTICO: {e}")

@bot.my_chat_member_handler()
def handle_bot_status_update(update):
    """Responde cuando el estado del bot cambia en un chat"""
    try:
        chat_id = update.chat.id
        new_status = update.new_chat_member.status
        old_status = update.old_chat_member.status
        
        print("\n==================================================")
        print(f"🔄🔄🔄 ESTADO DEL BOT ACTUALIZADO EN CHAT: {chat_id} 🔄🔄🔄")
        print(f"🔄 De: {update.from_user.first_name} (ID: {update.from_user.id})")
        print(f"🔄 Estado anterior: {old_status} → Nuevo estado: {new_status}")
        print("==================================================\n")
        
        # El bot fue añadido al grupo (cambio de 'left' a otro estado)
        if old_status == 'left' and new_status != 'left':
            bot.send_message(
                chat_id,
                "¡Gracias por añadirme al grupo!\n\n"
                "Para poder configurar correctamente el grupo necesito ser administrador. "
                "Por favor, sigue estos pasos:\n\n"
                "1.Pulsa en el nombre del grupo\n"
                "2.Managed my chat\n"
                "3. Selecciona añadir 'Administradores'\n"
                "4. Añádeme como administrador\n\n"
                "Una vez me hayas hecho administrador, usa el comando /configurar_grupo."
            )
            
        # El bot fue promovido a administrador
        elif new_status == 'administrator' and old_status != 'administrator':
            bot.send_message(
                chat_id,
                "✅ ¡Gracias por hacerme administrador!\n\n"
                "Ahora puedo configurar correctamente este grupo. "
                "Si eres profesor, usa el comando /configurar_grupo para "
                "establecer este chat como una sala de tutoría."
            )
            
    except Exception as e:
        print(f"❌ ERROR EN MANEJADOR MY_CHAT_MEMBER: {e}")
        import traceback
        traceback.print_exc()

