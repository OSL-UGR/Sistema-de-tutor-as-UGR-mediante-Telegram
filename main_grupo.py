"""
Archivo principal del bot de grupos de tutorías.
Inicialización, configuración y handlers básicos.
"""
import telebot
import threading
import os
import sys
import logging
from dotenv import load_dotenv
from telebot import types


# Importar utilidades y handlers
from handlers_grupo.registro import COMMAND_CONFIGURAR_GRUPO
from handlers_grupo.tutorias import COMMAND_FINALIZAR
from handlers_grupo.utils import (
    menu_profesor, menu_estudiante, 
    configurar_logger, limpieza_periodica
)

# Configuración de logging
logger = configurar_logger()

# Cargar token del bot de grupos
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, "datos.env")

if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    logger.info(f"Cargando variables desde {env_path}")
else:
    load_dotenv()
    logger.warning("No se encontró archivo de variables específico")

# Estandarizar el nombre del token
BOT_TOKEN = os.getenv("BOT_TOKEN_GRUPO")
    
if not BOT_TOKEN:
    logger.critical("Token del bot de grupos no encontrado")
    print("El token del bot de grupos no está configurado. Añade BOT_TOKEN_GRUPO en datos.env.txt")
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

COMMAND_START = "start"
COMMAND_HELP = "help"

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

# Importar funciones de la base de datos compartidas
from db.queries import get_grupos_tutoria, get_usuarios
from db.constantes import *

# Handlers básicos
@bot.message_handler(commands=[COMMAND_START])
def send_welcome(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user = get_usuarios(USUARIO_ID_TELEGRAM=user_id)
    
    if not user:
        bot.send_message(
            chat_id,
            "👋 Bienvenido al sistema de tutorías en grupos.\n\n"
            "No te encuentro registrado en el sistema. Por favor, primero regístrate con el bot principal."
        )
        return
    user=user[0]

    # Actualizar interfaz según rol y tipo de chat
    if message.chat.type in ['group', 'supergroup']:
        # Estamos en un grupo
        grupo = get_grupos_tutoria(GRUPO_ID_CHAT=str(chat_id))
        
        if grupo:
            grupo=grupo[0]
            if (grupo[GRUPO_TIPO]==GRUPO_PRIVADO):
                # Es un grupo de tutoría registrado
                if user[USUARIO_TIPO] == USUARIO_TIPO_PROFESOR:
                    bot.send_message(
                        chat_id,
                        "👨‍🏫 *Bot de tutoría activo*\n\n"
                        "Este grupo está configurado como grupo de tutoría. Cuando recivas peticiones en el otro bot, si las aceptas, se invitaran alumnos al grupo.",
                        reply_markup=menu_profesor(),
                        parse_mode="Markdown"
                    )
                else:
                    # Es estudiante
                    bot.send_message(
                        chat_id,
                        "👨‍🎓 *Bot de tutoría activo*\n\n"
                        "Cuando termines tu consulta, usa el botón o haz /finalizar para finalizar la tutoría.",
                        reply_markup=menu_estudiante(),
                        parse_mode="Markdown"
                    )
        else:
            # No es un grupo registrado
            if user[USUARIO_TIPO] == USUARIO_TIPO_PROFESOR:
                bot.send_message(
                    chat_id,
                    "Este grupo no está configurado como grupo de tutoría. Usa /configurar_grupo para configurarlo."
                )
    else:
        # Es un chat privado
        if user[USUARIO_TIPO] == USUARIO_TIPO_PROFESOR:
            bot.send_message(
                chat_id,
                f"¡Bienvenido, Profesor! Invitame a un grupo, dame permisos de administrador y ejecuta /{COMMAND_CONFIGURAR_GRUPO} para establecer un grupo",
                reply_markup=menu_profesor()
            )
        else:
            # Es estudiante
            bot.send_message(
                chat_id,
                "¡Hola! Para unirte a una tutoría, necesitas el enlace de invitación de tu profesor.",
                reply_markup=menu_estudiante()
            )
    
    logger.info(f"Usuario {user_id} ({user[USUARIO_NOMBRE]}) ha iniciado el bot en chat {chat_id}")

@bot.message_handler(commands=[COMMAND_HELP])
def help_handler(message):
    chat_id = message.chat.id
    bot.send_message(
        chat_id,
        "ℹ️ *Ayuda del Bot*\n\n"
        "🔹 Usa los siguientes comandos para interactuar con el bot:\n"
        f"✅ /{COMMAND_START} - Almacena tus datos y te da la bienvenida si eres estudiante.\n"
        f"✅ /{COMMAND_HELP} - Muestra este mensaje de ayuda.\n"
        f"✅ /{COMMAND_FINALIZAR} o Pulsa el botón '❌ Terminar Tutoria' para finalizar la tutoria actual.\n",
        parse_mode="Markdown"
    )
    logger.info(f"Mensaje de ayuda enviado a {chat_id}")

# Iniciar hilo de limpieza periódica
# Reemplazar la función configurar_grupo actual con esta versión mejorada:
# Handler para cuando un grupo es creado
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
                "establecer este chat como una grupo de tutoría."
            )
            
    except Exception as e:
        print(f"❌ ERROR EN MANEJADOR MY_CHAT_MEMBER: {e}")
        import traceback
        traceback.print_exc()


def setup_commands():
    """Configura los comandos que aparecen en el menú del bot"""
    try:
        bot.set_my_commands([
            types.BotCommand(f'/{COMMAND_START}', 'Iniciar el bot'),
            types.BotCommand(f'/{COMMAND_CONFIGURAR_GRUPO}', 'Configuración inicial del grupo'),
            types.BotCommand(f'/{COMMAND_HELP}', 'Mostrar ayuda del bot'),
            types.BotCommand(f'/{COMMAND_FINALIZAR}', 'Finalizar una sesión de tutoría'),
        ])
        print("✅ Comandos del bot configurados correctamente")
        return True
    except Exception as e:
        print(f"❌ Error al configurar los comandos del bot: {e}")
        return False

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

    setup_commands()
    
    try:
        # Registrar handlers de usuarios primero para darle prioridad
        from handlers_grupo.usuarios import register_handlers as registrar_handlers_usuarios
        from handlers_grupo.registro import register_handlers as registrar_handlers_registro
        from handlers_grupo.tutorias import register_handlers as registrar_handlers_tutorias
        registrar_handlers_usuarios(bot)
        registrar_handlers_registro(bot)
        registrar_handlers_tutorias(bot)
        print("✅ Handler de nuevos estudiantes registrado")
                
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