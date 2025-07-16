import telebot
from telebot import types
import re
import sys
import os
import time
import random
import logging
from email.message import EmailMessage
import smtplib
from pathlib import Path

from config import SMTP_EMAIL, SMTP_PASSWORD, SMTP_SERVER
from db.constantes import USUARIO_TIPO, USUARIO_TIPO_ESTUDIANTE
from handlers.grupos import COMMAND_CREAR_GRUPO_TUTORIA
from handlers.horarios import COMMAND_CONFIGURAR_HORARIO
from handlers.tutorias import COMMAND_TUTORIA
from handlers.valoraciones import COMMAND_VALORAR_PROFESOR, COMMAND_VER_VALORACIONES
from utils.state_manager import *

# Añadir directorio raíz al path para resolver importaciones
sys.path.append(str(Path(__file__).parent.parent))

# Añadir directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar módulos necesarios
from db.queries import (get_usuarios, update_usuario)
from db.constantes import *
# Añadir al inicio del archivo
from utils.state_manager import *

# Variables para seguridad de token
token_intentos_fallidos = {}  # {chat_id: número de intentos}
token_bloqueados = {}  # {chat_id: tiempo de desbloqueo}
token_usados = set()  # Conjunto de tokens ya utilizados

# No puedo importarlos de main
COMMAND_HELP = "help"
COMMAND_VER_MIS_DATOS = "ver_misdatos"

COMMAND_START = "start"

# Calldata
CANCELAR_REGISTRO = "cancelar_registro"

# Estados del proceso de registro
STATE_EMAIL = "registro_email"
STATE_VERIFY_TOKEN = "registro_verificacion"
STATE_CONFIRMAR_DATOS = "confirmando_datos_excel"

# Configurar logger
logger = logging.getLogger("registro")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', filename='logs/registro.log')


def register_handlers(bot):
    """Registra todos los handlers del proceso de registro"""
    
    def handle_registration_completion(chat_id, tipo_usuario):
        """Envía mensaje de bienvenida según tipo de usuario"""
        try:
            bot.send_message(
                chat_id, 
                "¡Bienvenido al sistema de tutorías! Usa /help para ver los comandos disponibles."
            )
        except Exception as e:
            logger.error(f"Error al enviar mensaje de bienvenida: {e}")
            

    def send_verification_email(email, token):
        """Envía un correo electrónico con el token de verificación"""
        # Cargar credenciales sin valores predeterminados para datos sensibles
        smtp_server = SMTP_SERVER
        sender_email = SMTP_EMAIL
        password = SMTP_PASSWORD
        
        # Verificar todas las credenciales necesarias
        if not all([smtp_server, sender_email, password]):
            missing = []
            if not smtp_server: missing.append("SMTP_SERVER")
            if not sender_email: missing.append("SMTP_EMAIL")  
            if not password: missing.append("SMTP_PASSWORD")
            logger.error(f"Faltan credenciales en datos.env.txt: {', '.join(missing)}")
            return False
        
        msg = EmailMessage()
        msg["From"] = sender_email
        msg["To"] = email
        msg["Subject"] = "Token tutorChatBot"
        
        # Create a more attractive HTML email
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #0066cc; color: white; padding: 15px; text-align: center; border-radius: 5px 5px 0 0;">
                <h2>Verificación de Asistente de Tutorías</h2>
            </div>
            <div style="padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 5px 5px;">
                <p>Hola,</p>
                <p>Gracias por registrarte en el <strong>Asistente de Tutorías</strong>. Para completar tu registro, utiliza el siguiente código de verificación:</p>
                <div style="background-color: #f5f5f5; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 5px; margin: 20px 0; border-radius: 5px;">
                    {token}
                </div>
                <p>Este código es válido durante <strong>3 minutos</strong>. Si no has solicitado este código, puedes ignorar este correo.</p>
                <p>Saludos,<br>El equipo del Asistente de Tutorías</p>
            </div>
            <div style="text-align: center; font-size: 12px; color: #777; margin-top: 20px;">
                <p>Este es un correo automático, por favor no respondas a este mensaje.</p>
            </div>
        </body>
        </html>
        """
        msg.set_content("Tu código de verificación es: " + token)
        msg.add_alternative(html_content, subtype='html')

        try:
            with smtplib.SMTP(str(smtp_server), 587) as server:
                server.ehlo()
                server.starttls()
                # Add explicit type assertion since we've already validated these aren't None
                server.login(str(sender_email), str(password))
                server.send_message(msg)
            
            # También registramos el token en el log/consola para desarrollo
            logger.info(f"TOKEN DE VERIFICACIÓN enviado a {email}: {token}")
            print(f"TOKEN DE VERIFICACIÓN enviado a {email}: {token}")
            return True
        except Exception as e:
            logger.error(f"Error en el envío del correo a {email}: {e}")
            print(f"Error en el envío del correo: {e}")
            return False

    def is_valid_email(email):
        """Verifica si el correo es válido (institucional UGR)"""
        #return re.match(r'.+@(correo\.)?ugr\.es$', email) is not None
        return re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email) is not None
        
    @bot.message_handler(commands=[COMMAND_START])
    def handle_start(message):
        """Inicia el proceso de registro simplificado"""
        chat_id = message.chat.id

        setup_commands(chat_id)

        user = get_usuarios(USUARIO_ID_TELEGRAM=chat_id)

        print(user)

        # Verifica si el usuario ya está registrado
        if user and user != []:
            bot.send_message(chat_id, "Ya estás registrado. Puedes usar las funcionalidades disponibles.")
            clear_state(chat_id)
            return

        # Inicia el proceso simplificado pidiendo solo el correo
        bot.send_message(
            chat_id, 
            "🤖 *¡Bienvenido al Asistente de Tutorías UGR!* 🎓\n\n"
            "Este bot te permite acceder a tutorías académicas con profesores y estudiantes "
            "de forma sencilla y organizada.\n\n"
            "Para comenzar, necesito verificar tu cuenta institucional.\n\n"
            "Por favor, introduce tu correo electrónico de la UGR:\n"
            "• Estudiantes: usuario@correo.ugr.es\n"
            "• Profesores: usuario@ugr.es",
            parse_mode="Markdown"
        )
        set_state(chat_id, STATE_EMAIL)
        user_data[chat_id] = {}  # Reinicia los datos del usuario

    @bot.message_handler(func=lambda message: get_state(message.chat.id) == STATE_EMAIL)
    def handle_email(message):
        """Procesa el correo electrónico y envía código de verificación"""
        chat_id = message.chat.id
        text = message.text.strip()
        
        # Comprobar si está bloqueado
        if chat_id in token_bloqueados:
            if time.time() < token_bloqueados[chat_id]:
                tiempo_restante = int((token_bloqueados[chat_id] - time.time()) / 60)
                bot.send_message(
                    chat_id,
                    f"⛔ Tu cuenta está bloqueada temporalmente.\n"
                    f"Debes esperar {tiempo_restante} minutos antes de intentarlo de nuevo.",
                    reply_markup=telebot.types.ReplyKeyboardRemove()
                )
                return
            else:
                # Ya pasó el tiempo de bloqueo
                del token_bloqueados[chat_id]
                if chat_id in token_intentos_fallidos:
                    del token_intentos_fallidos[chat_id]
        
        # Validar el email
        email = text.lower()
        
        # 1. Verificar formato del correo
        if not is_valid_email(email):
            bot.send_message(
                chat_id, 
                "⚠️ El correo debe ser institucional (@ugr.es o @correo.ugr.es).\n"
                "Por favor, introduce un correo válido:"
            )
            return
        
        user = get_usuarios(USUARIO_EMAIL=email)
        
        # 2. Verificar si el correo existe en la tabla Usuarios
        if user is None:
            bot.send_message(
                chat_id, 
                "❌ *Correo no encontrado*\n\n"
                "El correo introducido no está registrado en el sistema.\n"
                "Solo pueden acceder usuarios previamente registrados en la base de datos.",
                parse_mode="Markdown"
            )
            return

        # 3. Verificar si el correo ya está registrado con un Telegram ID
        if user[0][USUARIO_ID_TELEGRAM] is not None:
            bot.send_message(
                chat_id, 
                "⚠️ Este correo ya está registrado. Si ya tienes cuenta, usa los comandos disponibles.\n"
                "Si necesitas ayuda, contacta con soporte."
            )
            clear_state(chat_id)
            return
        
        # Guardar el email
        user_data[chat_id][USUARIO_EMAIL] = email
        
        # Generar token seguro de 6 dígitos
        token = str(random.randint(100000, 999999))
        user_data[chat_id][TOKEN] = token
        user_data[chat_id][TOKEN_EXPIRY] = time.time() + 180  # Token válido por 3 minutos
        
        # Determinar tipo de usuario por el correo
        es_estudiante = email.endswith("@correo.ugr.es")
        user_data[chat_id][USUARIO_TIPO] = USUARIO_TIPO_ESTUDIANTE if es_estudiante else USUARIO_TIPO_PROFESOR
        
        # Enviar token de verificación
        if send_verification_email(email, token):
            # Botón para cancelar
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("❌ Cancelar", callback_data=CANCELAR_REGISTRO))
            
            bot.send_message(
                chat_id, 
                "🔑 *Verificación de Cuenta*\n\n"
                "Se ha enviado un código de 6 dígitos a tu correo.\n"
                "Por favor, introduce el código que has recibido.\n\n"
                "⏱️ *El código expirará en 3 minutos*\n\n"
                "_Si no lo recibes, verifica tu carpeta de spam._",
                parse_mode="Markdown",
                reply_markup=markup
            )
            set_state(chat_id, STATE_VERIFY_TOKEN)
        else:
            bot.send_message(
                chat_id, 
                "❌ *Error al enviar el código de verificación*\n\n"
                "No ha sido posible enviar el email con tu código.\n"
                "Por favor, intenta nuevamente más tarde o contacta con soporte.\n\n"
                "_Para desarrollo: revisa los logs y la configuración SMTP._",
                parse_mode="Markdown"
            )
            clear_state(chat_id)

    def mostrar_menu_principal(message):
        """Muestra el menú principal según el tipo de usuario"""
        chat_id = message.chat.id
        
        if chat_id not in user_data:
            # Si no hay datos del usuario, mostrar mensaje genérico
            bot.send_message(
                chat_id,
                "🤖 Bienvenido al Asistente de Tutorías UGR\n\n"
                "Usa /help para ver los comandos disponibles."
            )
            return
            
        # Mensaje según tipo de usuario
        if user_data[chat_id][USUARIO_TIPO] == USUARIO_TIPO_ESTUDIANTE:
            mensaje = (
                f"📚 *Comandos disponibles:*\n"
                f"• /help - Ver todos los comandos disponibles\n"
            )
        else:  # Si es profesor
            mensaje = (
                f"🔔 *Tu próximo paso:*\n"
                f"Debes crear un grupo de tutoría para cada asignatura que impartes.\n"
                f"Utiliza el comando /crear_grupo para configurar tus grupos.\n\n"
                f"📚 *Otros comandos disponibles:*\n"
                f"• /help - Ver todos los comandos disponibles\n"
            )

        bot.send_message(
            chat_id,
            mensaje,
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda message: get_state(message.chat.id) == STATE_VERIFY_TOKEN)
    def verificar_token(message):
        chat_id = message.chat.id
        token_ingresado = message.text.strip()
        
        # Validar el token
        es_valido = False
        if chat_id in user_data and TOKEN in user_data[chat_id]:
            token_almacenado = user_data[chat_id].get(TOKEN)
            token_expiry = user_data[chat_id].get(TOKEN_EXPIRY, 0)
            
            if token_ingresado == token_almacenado and time.time() < token_expiry:
                es_valido = True
            elif time.time() >= token_expiry:
                bot.send_message(chat_id, f"⚠️ El código ha expirado. Por favor, solicita uno nuevo con /{COMMAND_START}")
                clear_state(chat_id)
                return
            else:
                bot.send_message(chat_id, "❌ Código incorrecto. Inténtalo de nuevo")
                return
    
        if es_valido:
            try:
                # Obtener el correo asociado con este chat_id
                email = user_data[chat_id][USUARIO_EMAIL]
                tipo_usuario = user_data[chat_id].get(USUARIO_TIPO, USUARIO_TIPO_ESTUDIANTE)
                
                if email:
                    # Actualizar la base de datos: cambiar Registrado a SI y guardar el TelegramID
                    user = get_usuarios(USUARIO_EMAIL=email)[0]  # Verificar que el email existe
                    update_usuario(user[USUARIO_ID], USUARIO_ID_TELEGRAM=message.from_user.id)
                    logger.info(f"Usuario {email} verificado correctamente. TelegramID actualizado.")

                    setup_commands(chat_id)
                    
                    # Enviar mensaje de bienvenida
                    handle_registration_completion(chat_id, tipo_usuario)
                        
                else:
                    logger.error("No se encontró email en user_data para la verificación")
            except Exception as e:
                logger.error(f"Error al actualizar registro en BD: {e}")
        
        # Confirmar al usuario y cambiar estado
        bot.send_message(message.chat.id, "✅ Verificación exitosa!")
        clear_state(message.chat.id)  # Limpiar estado
        
        # Mostrar menú principal o siguiente paso
        mostrar_menu_principal(message)

    @bot.callback_query_handler(func=lambda call: call.data == CANCELAR_REGISTRO)
    def handle_cancelar_registro(call):
        """Cancela el proceso de registro"""
        chat_id = call.message.chat.id
        
        bot.send_message(
            chat_id, 
            f"Registro cancelado. Puedes iniciarlo nuevamente con /{COMMAND_START} cuando lo desees.",
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )
        clear_state(chat_id)
        bot.answer_callback_query(call.id)

        if user_data[chat_id][USUARIO_TIPO] == USUARIO_TIPO_ESTUDIANTE:
            mensaje = (
                f"📚 *Comandos disponibles:*\n"
                f"• /help - Ver todos los comandos disponibles\n"
            )
        else:  # Si es profesor
            mensaje = (
                f"🔔 *Tu próximo paso:*\n"
                f"Debes configurar tu horario de tutorías y crear grupos para tus asignaturas.\n\n"
                f"📚 *Comandos disponibles:*\n"
                f"• /help - Ver todos los comandos disponibles"
            )
        
        bot.send_message(
            chat_id,
            mensaje,
            parse_mode="Markdown"
        )
            
        # Limpiar estado para terminar el registro
        clear_state(chat_id)
        bot.answer_callback_query(call.id, "✅ Registro completado")


    def setup_commands(chat_id = ""):
        """Configura los comandos que aparecen en el menú del bot"""
        try:
            bot.delete_my_commands(scope=telebot.types.BotCommandScopeChat(chat_id))
            user = get_usuarios(USUARIO_ID_TELEGRAM=chat_id)
            if user and user[0][USUARIO_TIPO] == USUARIO_TIPO_ESTUDIANTE:
                bot.set_my_commands([
                    telebot.types.BotCommand(f"/{COMMAND_START}", "Inicia el bot, el registro y actualiza el menu de comandos"),
                    telebot.types.BotCommand(f"/{COMMAND_HELP}", "Muestra la ayuda del bot"),
                    telebot.types.BotCommand(f"/{COMMAND_TUTORIA}", "Ver profesores disponibles para tutoría"),
                    telebot.types.BotCommand(f"/{COMMAND_VALORAR_PROFESOR}", "Valora un profesor"),
                    telebot.types.BotCommand(f"/{COMMAND_VER_MIS_DATOS}", "Ver tus datos registrados")
                ], scope=telebot.types.BotCommandScopeChat(chat_id))
            elif user and user[0][USUARIO_TIPO] == USUARIO_TIPO_PROFESOR:
                bot.set_my_commands([
                    telebot.types.BotCommand(f"/{COMMAND_START}", "Inicia el bot, el registro y actualiza el menu de comandos"),
                    telebot.types.BotCommand(f"/{COMMAND_HELP}", "Muestra la ayuda del bot"),
                    telebot.types.BotCommand(f"/{COMMAND_VER_VALORACIONES}", "Ver valoraciones tuyas de alumnos"),
                    telebot.types.BotCommand(f"/{COMMAND_CREAR_GRUPO_TUTORIA}", "Crea un grupo de tutoría"),
                    telebot.types.BotCommand(f"/{COMMAND_CONFIGURAR_HORARIO}", "Configura tu horario de tutorías"),
                    telebot.types.BotCommand(f"/{COMMAND_VER_MIS_DATOS}", "Ver tus datos registrados")
                ], scope=telebot.types.BotCommandScopeChat(chat_id))
            else:
                bot.set_my_commands([
                    telebot.types.BotCommand(f"/{COMMAND_START}", "Inicia el bot, el registro y actualiza el menu de comandos"),
                    telebot.types.BotCommand(f"/{COMMAND_HELP}", "Muestra la ayuda del bot"),
                ], scope=telebot.types.BotCommandScopeChat(chat_id))
                
            print("✅ Comandos del bot configurados correctamente")
            return True
        except Exception as e:
            print(f"❌ Error al configurar los comandos del bot: {e}")
            return False