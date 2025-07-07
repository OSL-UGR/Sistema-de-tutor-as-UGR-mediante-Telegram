import telebot
import time
import threading
from telebot import types
import os
import sys
from config import BOT_TOKEN, DB_PATH,EXCEL_PATH
from db.db import close_connection
from db.queries import get_grupos_tutoria, get_matriculas, get_usuarios
from db.constantes import *

# Reemplaza todos los handlers universales por este ÚNICO handler al final
# Inicializar el bot de Telegram
bot = telebot.TeleBot(BOT_TOKEN) 

def escape_markdown(text):
    """Escapa caracteres especiales de Markdown"""
    if not text:
        return ""
    
    chars = ['_', '*', '`', '[', ']', '(', ')', '#', '+', '-', '.', '!']
    for char in chars:
        text = text.replace(char, '\\' + char)
    
    return text

def setup_commands():
    """Configura los comandos que aparecen en el menú del bot"""
    try:
        bot.set_my_commands([
            telebot.types.BotCommand("/start", "Inicia el bot y el registro"),
            telebot.types.BotCommand("/help", "Muestra la ayuda del bot"),
            telebot.types.BotCommand("/tutoria", "Ver profesores disponibles para tutoría"),
            telebot.types.BotCommand("/valorar_profesor", "Valora un profesor"),
            telebot.types.BotCommand("/crear_grupo_tutoria", "Crea un grupo de tutoría"),
            telebot.types.BotCommand("/configurar_horario", "Configura tu horario de tutorías"),
            telebot.types.BotCommand("/ver_misdatos", "Ver tus datos registrados")
        ])
        print("✅ Comandos del bot configurados correctamente")
        return True
    except Exception as e:
        print(f"❌ Error al configurar los comandos del bot: {e}")
        return False

@bot.message_handler(commands=['help'])
def handle_help(message):
    """Muestra la ayuda del bot"""
    chat_id = message.chat.id
    user = get_usuarios(USUARIO_ID_TELEGRAM=message.from_user.id)
    
    if not user:
        bot.send_message(
            chat_id,
            "❌ No estás registrado. Usa /start para registrarte."
        )
        return
    user = user[0]
    
    help_text = (
        "🤖 *Comandos disponibles:*\n\n"
        "/start - Inicia el bot y el proceso de registro\n"
        "/help - Muestra este mensaje de ayuda\n"
        
    )
    if user[USUARIO_TIPO] == USUARIO_TIPO_ESTUDIANTE:
        help_text += (
            "/tutoria - Ver profesores disponibles para tutoría\n"
            "/ver_misdatos - Ver tus datos registrados\n"
            "/valorar_profesor - Dar una valoración a un profesor\n"
        )

    if user[USUARIO_TIPO] == USUARIO_TIPO_PROFESOR:
        help_text += (
            "/configurar_horario - Configura tu horario de tutorías\n"
            "/crear_grupo_tutoria - Crea un grupo de tutoría\n"
        )
    
    # Escapar los guiones bajos para evitar problemas de formato
    help_text = help_text.replace("_", "\\_")
    
    try:
        bot.send_message(chat_id, help_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Error al enviar mensaje de ayuda: {e}")
        # Si falla, envía sin formato
        bot.send_message(chat_id, help_text.replace('*', ''), parse_mode=None)

@bot.message_handler(commands=['ver_misdatos'])
def handle_ver_misdatos(message):
    chat_id = message.chat.id
    print(f"\n\n### INICIO VER_MISDATOS - Usuario: {message.from_user.id} ###")
    print(message.from_user.id)
    
    user = get_usuarios(USUARIO_ID_TELEGRAM=message.from_user.id)
    
    if not user:
        print("⚠️ Usuario no encontrado en BD")
        bot.send_message(chat_id, "❌ No estás registrado. Usa /start para registrarte.")
        return
    
    user = user[0]
    print(f"✅ Usuario encontrado: {user[USUARIO_NOMBRE]} ({user[USUARIO_TIPO]})")
    
    # Convertir el objeto sqlite3.Row a diccionario
    user_dict = dict(user)
    
    # Obtener matrículas del usuario
    matriculas = get_matriculas(MATRICULA_ID_USUARIO=user[USUARIO_ID])
    
    user_info = (
        f"👤 *Datos de usuario:*\n\n"
        f"*Nombre:* {user[USUARIO_NOMBRE]}\n"
        f"*Correo:* {user[USUARIO_EMAIL] or 'No registrado'}\n"
        f"*Tipo:* {user[USUARIO_TIPO].capitalize()}\n"
    )
    
    # Añadir la carrera desde la tabla Usuarios
    if 'Carrera' in user_dict and user_dict[USUARIO_CARRERA]:
        user_info += f"*Carrera:* {user_dict[USUARIO_CARRERA]}\n\n"
    else:
        user_info += "*Carrera:* No registrada\n\n"
    
    # Añadir información de matrículas
    if matriculas and len(matriculas) > 0:
        user_info += "*Asignaturas matriculadas:*\n"
        
        # Agrupar asignaturas por carrera
        for m in matriculas:
            # Convertir cada matrícula a diccionario si es necesario
            m_dict = dict(m) if hasattr(m, 'keys') else m
            asignatura = m_dict.get(MATRICULA_ASIGNATURA, 'Desconocida')
            user_info += f"- {asignatura}\n"
    else:
        user_info += "No tienes asignaturas matriculadas.\n"
    
    # Añadir horario si es profesor
    if user[USUARIO_TIPO] == USUARIO_TIPO_PROFESOR:
        if USUARIO_HORARIO in user_dict and user_dict[USUARIO_HORARIO]:
            user_info += f"\n*Horario de tutorías:*\n{user_dict[USUARIO_HORARIO]}\n\n"
        
        # NUEVA SECCIÓN: Mostrar grupos creadas por el profesor        
        # Consultar todas las grupos creadas por este profesor  
        grupos = get_grupos_tutoria(GRUPO_ID_USUARIO=user[USUARIO_ID])
        print(grupos)
        grupos.sort(key=lambda x: x[GRUPO_FECHA], reverse=True)
        
        if grupos and len(grupos) > 0:
            user_info += "\n*🔵 grupos de tutoría creadas:*\n"
            
            # Diccionario para traducir los propósitos a texto más amigable
            propositos = {
                'individual': 'Tutorías individuales',
                'grupal': 'Tutorías grupales',
                'avisos': 'Canal de avisos'
            }
            
            for grupo in grupos:
                # Obtener propósito en formato legible
                proposito = propositos.get(grupo[GRUPO_PROPOSITO], grupo[GRUPO_PROPOSITO] or 'General')
                
                # Obtener asignatura o indicar que es general
                asignatura = grupo[GRUPO_ASIGNATURA] or 'General'
                
                # Formato de fecha más amigable
                fecha = grupo[GRUPO_FECHA].split(' ')[0] if grupo[GRUPO_FECHA] else 'Desconocida'
                
                user_info += f"• *{grupo[GRUPO_NOMBRE]}*\n"
                user_info += f"  📋 Propósito: {proposito}\n"
                user_info += f"  📚 Asignatura: {asignatura}\n"
                user_info += f"  📅 Creada: {fecha}\n\n"
        else:
            user_info += "\n*🔵 No has creado grupos de tutoría todavía.*\n"
            user_info += "Usa /crear_ grupo _ tutoria para crear una nueva grupo.\n"
    
    # Intentar enviar el mensaje con formato Markdown
    try:
        bot.send_message(chat_id, user_info, parse_mode="Markdown")
        
        # Si es profesor y tiene grupos, mostrar botones para editar
        if user[USUARIO_TIPO] == USUARIO_TIPO_PROFESOR and grupos and len(grupos) > 0:
            markup = types.InlineKeyboardMarkup(row_width=1)
            
            # Añadir SOLO botones para editar cada grupo (quitar botones de eliminar)
            for grupo in grupos:
                grupo_id = grupo[GRUPO_ID]
                
                markup.add(types.InlineKeyboardButton(
                    f"✏️ grupo: {grupo[GRUPO_NOMBRE]}",
                    callback_data=f"edit_grupo_{grupo_id}"
                ))
            
            bot.send_message(
                chat_id,
                "Selecciona una grupo para gestionar:",
                reply_markup=markup
            )
    except Exception as e:
        # Si falla por problemas de formato, enviar sin formato
        print(f"Error al enviar datos de usuario: {e}")
        bot.send_message(chat_id, user_info.replace('*', ''), parse_mode=None)

# Importar y configurar los handlers desde los módulos
from handlers.registro import register_handlers as register_registro_handlers
from handlers.tutorias import register_handlers as register_tutorias_handlers
from handlers.grupos import register_handlers as register_grupos_handlers
from handlers.horarios import register_handlers as register_horarios_handlers
from handlers.valoraciones import register_handlers as register_valoraciones_handlers

# Registrar todos los handlers
register_registro_handlers(bot)
register_tutorias_handlers(bot)
register_horarios_handlers(bot)
register_valoraciones_handlers(bot)
register_grupos_handlers(bot)

def setup_polling():
    """Configura el polling para el bot y maneja errores"""
    print("🤖 Iniciando el bot...")
    try:
        # Configurar comandos disponibles
        if setup_commands():
            print("✅ Comandos configurados correctamente")
        else:
            print("⚠️ Error al configurar comandos")
        
        # Agregar esta línea:
        print("⚙️ Configurando polling con eventos de grupo...")
        
        # Modificar esta línea:
        bot.infinity_polling(
            timeout=10, 
            long_polling_timeout=5,
            allowed_updates=["message", "callback_query", "my_chat_member", "chat_member"]
        )
    except KeyboardInterrupt:
        print("👋 Bot detenido manualmente")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        
        # Reintentar después de un tiempo
        print("🔄 Reintentando en 10 segundos...")
        time.sleep(10)
        setup_polling()

if __name__ == "__main__":
    print("="*50)
    print("🎓 SISTEMA DE TUTORÍAS UGR")
    print("="*50)
    print(f"📅 Fecha de inicio: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💾 Base de datos: {DB_PATH}")
    print(f"📊 Excel de datos: {EXCEL_PATH}")
    print("="*50)
    
    # Iniciar el bot
    try:
        setup_polling()
    finally:
        close_connection()
        print("🔒 Conexión a la base de datos cerrada")