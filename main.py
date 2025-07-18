import telebot
import time
from telebot import types
import sys
from config import BOT_TOKEN
from db import close_connection
from db.queries import get_grupos_tutoria, get_matriculas, get_usuarios
from db.constantes import *
from handlers.commands import *

# Inicializar el bot de Telegram
bot = telebot.TeleBot(BOT_TOKEN) 

@bot.message_handler(commands=[COMMAND_HELP])
def handle_help(message):
    """Muestra la ayuda del bot"""
    chat_id = message.chat.id
    user = get_usuarios(USUARIO_ID_TELEGRAM=message.from_user.id)
    
    if not user:
        bot.send_message(
            chat_id,
            f"❌ No estás registrado. Usa /{COMMAND_START} para registrarte."
        )
        return
    user = user[0]
    
    help_text = (
        "🤖 *Comandos disponibles:*\n\n"
        f"/{COMMAND_START} - Inicia el bot, el registro y actualiza el menu de comandos\n"
        f"/{COMMAND_HELP} - Muestra este mensaje de ayuda\n"
        
    )
    if user[USUARIO_TIPO] == USUARIO_TIPO_ESTUDIANTE:
        help_text += (
            f"/{COMMAND_TUTORIA} - Ver profesores disponibles para tutoría\n"
            f"/{COMMAND_VER_MIS_DATOS} - Ver tus datos registrados\n"
            f"/{COMMAND_VALORAR_PROFESOR} - Dar una valoración a un profesor\n"
        )

    if user[USUARIO_TIPO] == USUARIO_TIPO_PROFESOR:
        help_text += (
            f"/{COMMAND_CONFIGURAR_HORARIO} - Configura tu horario de tutorías\n"
            f"/{COMMAND_CREAR_GRUPO_TUTORIA} - Crea un grupo de tutoría\n"
            f"/{COMMAND_VER_VALORACIONES} - Muestra datos de tus valoraciones\n"
        )
    
    # Escapar los guiones bajos para evitar problemas de formato
    help_text = help_text.replace("_", "\\_")
    
    try:
        bot.send_message(chat_id, help_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Error al enviar mensaje de ayuda: {e}")
        # Si falla, envía sin formato
        bot.send_message(chat_id, help_text.replace('*', ''), parse_mode=None)

@bot.message_handler(commands=[COMMAND_VER_MIS_DATOS])
def handle_ver_misdatos(message):
    chat_id = message.chat.id
    print(f"\n\n### INICIO VER_MISDATOS - Usuario: {message.from_user.id} ###")
    
    user = get_usuarios(USUARIO_ID_TELEGRAM=message.from_user.id)
    
    if not user:
        print("⚠️ Usuario no encontrado en BD")
        bot.send_message(chat_id, f"❌ No estás registrado. Usa /{COMMAND_START} para registrarte.")
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
        
    # Añadir información de matrículas
    if matriculas and len(matriculas) > 0:
        user_info += "*Asignaturas matriculadas:*\n"
        
        # Agrupar asignaturas por carrera
        for m in matriculas:
            # Convertir cada matrícula a diccionario si es necesario
            m_dict = dict(m) if hasattr(m, 'keys') else m
            asignatura = m_dict.get(MATRICULA_ASIGNATURA, 'Desconocida')
            user_info += f"  - {asignatura}\n"
    else:
        user_info += "No tienes asignaturas matriculadas.\n"
    
    # Añadir horario si es profesor
    if user[USUARIO_TIPO] == USUARIO_TIPO_PROFESOR:
        if USUARIO_HORARIO in user_dict and user_dict[USUARIO_HORARIO]:
            user_info += f"\n*Horario de tutorías:*"
            
            dias = user_dict[USUARIO_HORARIO].split(', ')
            
            dia_anterior = ""
            for dia in dias:
                dia = dia.split(' ')
                if dia[0] != dia_anterior:
                    user_info += f"\n  -{dia[0]} {dia[1]}"
                else:
                    user_info += f", {dia[1]}"
                dia_anterior = dia[0]
            
            user_info += "\n"
        # NUEVA SECCIÓN: Mostrar grupos creadas por el profesor        
        # Consultar todas las grupos creadas por este profesor  
        grupos = get_grupos_tutoria(GRUPO_ID_PROFESOR=user[USUARIO_ID])
        
        if grupos and len(grupos) > 0:
            print(grupos)
            grupos.sort(key=lambda x: x[GRUPO_FECHA], reverse=True)
            user_info += "\n*🔵 grupos de tutoría creadas:*\n"
            
            for grupo in grupos:
                # Obtener asignatura o indicar que es general
                asignatura = grupo[GRUPO_ASIGNATURA] or 'General'
                
                # Formato de fecha más amigable
                fecha = str(grupo[GRUPO_FECHA]).split(' ')[0] if grupo[GRUPO_FECHA] else 'Desconocida'
                
                user_info += f"• *{grupo[GRUPO_NOMBRE]}*\n"
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
                    callback_data=f"{EDIT_GRUPO}{grupo_id}"
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
from handlers.grupos import EDIT_GRUPO, register_handlers as register_grupos_handlers
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
    print("="*50)
    
    # Iniciar el bot
    try:
        setup_polling()
    finally:
        close_connection()
        print("🔒 Conexión a la base de datos cerrada")