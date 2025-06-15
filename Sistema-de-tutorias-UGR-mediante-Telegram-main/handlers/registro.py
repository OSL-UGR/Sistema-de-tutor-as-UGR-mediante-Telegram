import telebot
from telebot import types
import re
import sys
import os
import time
import random
import logging
from datetime import datetime
from email.message import EmailMessage
import smtplib
from pathlib import Path

# Añadir directorio raíz al path para resolver importaciones
sys.path.append(str(Path(__file__).parent.parent))

# Añadir directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar módulos necesarios
from utils.excel_manager import buscar_usuario_por_email, cargar_excel, verificar_email_en_excel, importar_datos_por_email
import pandas as pd
from db.queries import (
    get_user_by_telegram_id, 
    create_user, 
    crear_matricula,  
    get_db_connection,
    update_user,
    get_o_crear_carrera
)

# Añadir al inicio del archivo
from utils.state_manager import get_state, set_state, clear_state, user_data, user_states, estados_timestamp

# Variables para seguridad de token
token_intentos_fallidos = {}  # {chat_id: número de intentos}
token_bloqueados = {}  # {chat_id: tiempo de desbloqueo}
token_usados = set()  # Conjunto de tokens ya utilizados

# Estados del proceso de registro
STATE_EMAIL = "registro_email"
STATE_VERIFY_TOKEN = "registro_verificacion"
STATE_CONFIRMAR_DATOS = "confirmando_datos_excel"

# Configurar logger
logger = logging.getLogger("registro")
if not logger.handlers:
    handler = logging.FileHandler("registro.log")
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def register_handlers(bot):
    """Registra todos los handlers del proceso de registro"""
    
    def handle_registration_completion(chat_id, tipo_usuario):
        """Envía mensaje de bienvenida según tipo de usuario"""
        try:
            # Importar aquí para evitar importación circular
            from main import enviar_mensaje_bienvenida
            enviar_mensaje_bienvenida(chat_id, tipo_usuario)
        except Exception as e:
            logger.error(f"Error al enviar mensaje de bienvenida: {e}")
            bot.send_message(
                chat_id, 
                "¡Bienvenido al sistema de tutorías! Usa /help para ver los comandos disponibles."
            )
    
    def reset_user(chat_id):
        """Reinicia el estado y datos del usuario"""
        clear_state(chat_id)
    
    def is_user_registered(chat_id):
        """Verifica si el usuario ya está registrado"""
        user = get_user_by_telegram_id(chat_id)
        return user is not None
    
    def send_verification_email(email, token):
        """Envía un correo electrónico con el token de verificación"""
        # Cargar credenciales sin valores predeterminados para datos sensibles
        smtp_server = os.getenv("SMTP_SERVER")
        sender_email = os.getenv("SMTP_EMAIL")
        password = os.getenv("SMTP_PASSWORD")
        
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
    
    def verificar_correo_en_bd(email):
        """Verifica si el correo existe en la tabla Usuarios de la base de datos"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT Id_usuario FROM Usuarios WHERE Email_UGR = ?", (email,))
        resultado = cursor.fetchone()
        conn.close()
        return resultado is not None
    
    def is_email_registered(email):
        """Verifica si el correo ya está registrado en la base de datos"""
        # Implementar según tu estructura de base de datos
        # Por ahora siempre devuelve False
        return False
    
    def completar_registro(chat_id):
        """Completa el registro del usuario"""
        try:
            # Crear usuario
            user_id = create_user(
                nombre=user_data[chat_id]['nombre'],
                apellidos=user_data[chat_id]['apellidos'],
                tipo=user_data[chat_id]['tipo'],
                email=user_data[chat_id]['email'],
                telegram_id=chat_id,
                dni=user_data[chat_id].get('dni', ''),
                carrera=user_data[chat_id].get('carrera', '')
            )
            
            # Actualizar el campo carrera en la tabla usuarios
            update_user(user_id, Carrera=user_data[chat_id].get('carrera', ''))
            
            # Obtener o crear la carrera en la tabla Carreras
            carrera_id = get_o_crear_carrera(user_data[chat_id].get('carrera', 'General'))
            
            # Para estudiantes, crear matrículas
            if user_data[chat_id]['tipo'] == 'estudiante':
                for asignatura_id in user_data[chat_id].get('asignaturas_seleccionadas', []):
                    crear_matricula(user_id, asignatura_id)
                    # Asegurarse de que la asignatura esté asociada a la carrera
                    cursor = get_db_connection().cursor()
                    cursor.execute("UPDATE Asignaturas SET Id_carrera = ? WHERE Id_asignatura = ? AND Id_carrera IS NULL", 
                                  (carrera_id, asignatura_id))
                    cursor.connection.commit()
                    cursor.connection.close()
                    
            # Para profesores, crear asignaturas impartidas
            elif user_data[chat_id]['tipo'] == 'profesor':
                for asignatura_id in user_data[chat_id].get('asignaturas_seleccionadas', []):
                    crear_matricula(user_id, asignatura_id, 'profesor')
                    # Asegurarse de que la asignatura esté asociada a la carrera
                    cursor = get_db_connection().cursor()
                    cursor.execute("UPDATE Asignaturas SET Id_carrera = ? WHERE Id_asignatura = ? AND Id_carrera IS NULL", 
                                  (carrera_id, asignatura_id))
                    cursor.connection.commit()
                    cursor.connection.close()
        
            # Llamar a la función para enviar mensaje de bienvenida
            tipo = user_data[chat_id]['tipo']
            handle_registration_completion(chat_id, tipo)
            
            return True
        except Exception as e:
            logger.error(f"Error al completar registro: {e}")
            bot.send_message(chat_id, "❌ Error al completar el registro. Por favor, intenta de nuevo con /start.")
            return False

    def solicitar_carrera(chat_id):
        """Solicita al estudiante que seleccione su carrera"""
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        # Agregar carreras comunes como opciones rápidas
        markup.add("Ingeniería Informática", "Matemáticas")
        markup.add("Física", "Química")
        markup.add("Medicina", "Enfermería")
        markup.add("Derecho", "Economía")
        markup.add("Otra")
        
        bot.send_message(
            chat_id,
            "📚 Por favor, indica la carrera que estás cursando:",
            reply_markup=markup
        )
        
        # Establecer el estado para manejar la respuesta
        user_states[chat_id] = "esperando_carrera"
        estados_timestamp[chat_id] = time.time()
    
    @bot.message_handler(func=lambda message: user_states.get(message.chat.id) == "esperando_carrera")
    def handle_carrera(message):
        """Procesa la selección de carrera del estudiante"""
        chat_id = message.chat.id
        carrera = message.text.strip()
        
        # Guardar la carrera seleccionada
        user_data[chat_id]['carrera'] = carrera
        
        bot.send_message(
            chat_id,
            f"✅ Has seleccionado: {carrera}\n\nCompletando registro...",
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )
        
        # Continuar con el proceso de registro
        completar_registro(chat_id)
        
    @bot.message_handler(commands=["start"])
    def handle_start(message):
        """Inicia el proceso de registro simplificado"""
        chat_id = message.chat.id

        # Verifica si el usuario ya está registrado
        if is_user_registered(chat_id):
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
        user_states[chat_id] = STATE_EMAIL
        user_data[chat_id] = {}  # Reinicia los datos del usuario
        estados_timestamp[chat_id] = time.time()

    @bot.message_handler(func=lambda message: user_states.get(message.chat.id) == STATE_EMAIL)
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
        
        # 2. Verificar si el correo existe en la tabla Usuarios
        if not verificar_correo_en_bd(email):
            bot.send_message(
                chat_id, 
                "❌ *Correo no encontrado*\n\n"
                "El correo introducido no está registrado en el sistema.\n"
                "Solo pueden acceder usuarios previamente registrados en la base de datos.",
                parse_mode="Markdown"
            )
            return
        
        # 3. Verificar si el correo ya está registrado con un Telegram ID
        if is_email_registered(email):
            bot.send_message(
                chat_id, 
                "⚠️ Este correo ya está registrado. Si ya tienes cuenta, usa los comandos disponibles.\n"
                "Si necesitas ayuda, contacta con soporte."
            )
            clear_state(chat_id)
            return
        
        # Guardar el email
        user_data[chat_id]["email"] = email
        
        # Generar token seguro de 6 dígitos
        token = str(random.randint(100000, 999999))
        user_data[chat_id]["token"] = token
        user_data[chat_id]["token_expiry"] = time.time() + 180  # Token válido por 3 minutos
        
        # Determinar tipo de usuario por el correo
        es_estudiante = email.endswith("@correo.ugr.es")
        user_data[chat_id]["tipo"] = "estudiante" if es_estudiante else "profesor"
        
        # Enviar token de verificación
        if send_verification_email(email, token):
            # Botón para cancelar
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_registro"))
            
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
            user_states[chat_id] = STATE_VERIFY_TOKEN
            estados_timestamp[chat_id] = time.time()
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
        if user_data[chat_id].get("tipo") == "estudiante":
            mensaje = (
                f"📚 *Comandos disponibles:*\n"
                f"• /help - Ver todos los comandos disponibles\n"
                f"• /profesores - Ver profesores de tus asignaturas\n"
                f"• /horarios - Ver horarios de tutorías"
            )
        else:  # Si es profesor
            mensaje = (
                f"🔔 *Tu próximo paso:*\n"
                f"Debes crear un grupo de tutoría para cada asignatura que impartes.\n"
                f"Utiliza el comando /crear_grupo para configurar tus grupos.\n\n"
                f"📚 *Otros comandos disponibles:*\n"
                f"• /help - Ver todos los comandos disponibles\n"
                f"• /configurar_horario - Modificar tu horario de tutorías\n"
                f"• /mis_tutorias - Ver tus grupos de tutoría activos"
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
        if chat_id in user_data and "token" in user_data[chat_id]:
            token_almacenado = user_data[chat_id].get("token")
            token_expiry = user_data[chat_id].get("token_expiry", 0)
            
            if token_ingresado == token_almacenado and time.time() < token_expiry:
                es_valido = True
            elif time.time() >= token_expiry:
                bot.send_message(chat_id, "⚠️ El código ha expirado. Por favor, solicita uno nuevo con /start")
                clear_state(chat_id)
                return
            else:
                bot.send_message(chat_id, "❌ Código incorrecto. Inténtalo de nuevo o cancela con /cancelar")
                return
    
        if es_valido:
            try:
                # Obtener el correo asociado con este chat_id
                email = user_data[chat_id].get("email")
                tipo_usuario = user_data[chat_id].get("tipo", "estudiante")
                
                if email:
                    # Actualizar la base de datos: cambiar Registrado a SI y guardar el TelegramID
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE Usuarios SET Registrado = 'SI', TelegramID = ? WHERE Email_UGR = ?", 
                        (message.from_user.id, email)
                    )
                    
                    # Verificar que se actualizó alguna fila
                    if cursor.rowcount == 0:
                        bot.send_message(chat_id, "❌ No se encontró tu correo en la base de datos.")
                        logger.error(f"No se encontró el email {email} en la base de datos")
                    else:
                        conn.commit()
                        logger.info(f"Usuario {email} verificado correctamente. TelegramID actualizado.")
                        
                        # Enviar mensaje de bienvenida
                        handle_registration_completion(chat_id, tipo_usuario)
                        
                    conn.close()
                else:
                    logger.error("No se encontró email en user_data para la verificación")
            except Exception as e:
                logger.error(f"Error al actualizar registro en BD: {e}")
        
        # Confirmar al usuario y cambiar estado
        bot.send_message(message.chat.id, "✅ Verificación exitosa!")
        clear_state(message.chat.id)  # Limpiar estado
        
        # Mostrar menú principal o siguiente paso
        mostrar_menu_principal(message)

    @bot.callback_query_handler(func=lambda call: call.data == "cancelar_registro")
    def handle_cancelar_registro(call):
        """Cancela el proceso de registro"""
        chat_id = call.message.chat.id
        
        bot.send_message(
            chat_id, 
            "Registro cancelado. Puedes iniciarlo nuevamente con /start cuando lo desees.",
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )
        clear_state(chat_id)
        bot.answer_callback_query(call.id)

        if user_data[chat_id]["tipo"] == "estudiante":
            mensaje = (
                f"📚 *Comandos disponibles:*\n"
                f"• /help - Ver todos los comandos disponibles\n"
                f"• /profesores - Ver profesores de tus asignaturas\n"
                f"• /horarios - Ver horarios de tutorías"
            )
        else:  # Si es profesor
            mensaje = (
                f"🔔 *Tu próximo paso:*\n"
                f"Debes configurar tu horario de tutorías y crear grupos para tus asignaturas.\n\n"
                f"📚 *Comandos disponibles:*\n"
                f"• /configurar_horario - Establecer tu horario de tutorías\n"
                f"• /crear_grupo_tutoria - Crear grupos para tus asignaturas\n"
                f"• /help - Ver todos los comandos disponibles"
            )
        
        bot.send_message(
            chat_id,
            mensaje,
            parse_mode="Markdown"
        )
        
        # Enviar mensaje de bienvenida personalizado
        try:
            from main import enviar_mensaje_bienvenida
            enviar_mensaje_bienvenida(chat_id, user_data[chat_id]["tipo"])
        except Exception as e:
            logger.error(f"Error al enviar mensaje de bienvenida: {e}")
            
        # Limpiar estado para terminar el registro
        clear_state(chat_id)
        bot.answer_callback_query(call.id, "✅ Registro completado")