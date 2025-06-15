import telebot
from telebot import types
import re
import datetime
import time
import logging
import sys
import os
# Add parent directory to system path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Now import after modifying the path
from db.models import get_db_connection

from db.queries import update_user, get_user_by_telegram_id, update_horario_profesor

# Configuración del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Estados para la conversación
SELECCIONANDO_DIA = "seleccionando_dia"
GESTION_FRANJAS = "gestion_franjas"
INTRODUCIR_FRANJA = "introducir_franja"
CONFIRMACION_GUARDAR = "confirmacion_guardar"
POST_ANADIR_FRANJA = "post_anadir_franja"
MODIFICAR_FRANJA = "modificar_franja"

# Diccionarios para almacenar estados y datos temporales
user_states = {}
user_data = {}
estados_timestamp = {}  # Para timeout de estados

# Tiempo de inactividad (30 minutos)
TIMEOUT = 30 * 60

def set_state(chat_id, state):
    """Establece el estado de la conversación para un usuario"""
    user_states[chat_id] = state
    estados_timestamp[chat_id] = time.time()

def clear_state(chat_id):
    """Limpia el estado de la conversación para un usuario"""
    if chat_id in user_states:
        del user_states[chat_id]
    if chat_id in estados_timestamp:
        del estados_timestamp[chat_id]

def check_timeout(chat_id):
    """Comprueba si ha pasado demasiado tiempo desde la última interacción"""
    if chat_id in estados_timestamp:
        if time.time() - estados_timestamp[chat_id] > TIMEOUT:
            clear_state(chat_id)
            return True
    return False

def formatear_horario_bonito(horario_dict):
    """Convierte un diccionario de horario en un string formateado para mostrar"""
    if not horario_dict:
        return "No hay horario configurado"
    
    resultado = []
    for dia, franjas in sorted(horario_dict.items()):
        if franjas:
            lineas_hora = [f"• {hora}" for hora in sorted(franjas)]
            resultado.append(f"📅 *{dia}*:\n{chr(10).join(lineas_hora)}")
    
    return "\n\n".join(resultado) if resultado else "No hay horario configurado"

def guardar_horario_bd(chat_id, horario_dict):
    """Guarda el horario en la base de datos"""
    try:
        # Convertir el diccionario a string para guardar en la BD
        horario_str = ""
        for dia, franjas in horario_dict.items():
            for franja in franjas:
                if horario_str:
                    horario_str += ", "
                horario_str += f"{dia} {franja}"
        
        # Obtener el ID del usuario a partir del ID de Telegram
        user = get_user_by_telegram_id(chat_id)
        if not user:
            logger.error(f"No se encontró usuario con telegram_id {chat_id}")
            return False
        
        user_id = user['Id_usuario']  # Obtener el ID de usuario real
        
        # Actualizar en la base de datos usando la función específica
        return update_horario_profesor(user_id, horario_str)
        
    except Exception as e:
        logger.error(f"Error al guardar horario en BD: {e}")
        return False

def cargar_horario_bd(chat_id):
    """Carga el horario desde la base de datos"""
    try:
        # DIAGNÓSTICO: Imprimir valores para depuración
        print(f"Intentando cargar horario para chat_id: {chat_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Asegurarse de que el cursor devuelva diccionarios en lugar de tuples
        # Este paso es clave para acceder usando nombres de columnas
        cursor.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
        
        # Verificar primero si el usuario existe
        cursor.execute("SELECT Id_usuario, Horario FROM Usuarios WHERE TelegramID = ?", (chat_id,))
        usuario = cursor.fetchone()
        
        if not usuario:
            print(f"No se encontró usuario con telegram_id {chat_id}")
            conn.close()
            return {}
        
        # Ahora podemos acceder por nombre de columna
        user_id = usuario['Id_usuario']
        print(f"ID de usuario encontrado: {user_id}")
        
        # DIAGNÓSTICO: Verificar si hay un valor directo en el campo Horario
        if usuario['Horario']:
            print(f"Horario encontrado en campo Usuarios.Horario: {usuario['Horario']}")
            # Intenta convertir el formato de cadena a diccionario
            try:
                horario_dict = {}
                franjas_str = usuario['Horario'].split(',')
                for franja in franjas_str:
                    franja = franja.strip()
                    if ' ' in franja:
                        dia, horas = franja.split(' ', 1)
                        if dia not in horario_dict:
                            horario_dict[dia] = []
                        horario_dict[dia].append(horas)
                print(f"Horario convertido a diccionario: {horario_dict}")
                return horario_dict
            except Exception as e:
                print(f"Error al convertir horario de cadena: {e}")
        
        # DIAGNÓSTICO: Si no hay horario en el campo directo, buscar en la tabla Horarios_Profesores
        print("Buscando en tabla Horarios_Profesores...")
        cursor.execute(
            "SELECT dia, hora_inicio, hora_fin FROM Horarios_Profesores WHERE Id_usuario = ?",
            (user_id,)
        )
        
        horarios = cursor.fetchall()
        print(f"Registros encontrados en Horarios_Profesores: {len(horarios) if horarios else 0}")
        
        conn.close()
        
        # Convertir a formato de diccionario
        horario_dict = {}
        for h in horarios:
            dia = h['dia']
            franja = f"{h['hora_inicio']}-{h['hora_fin']}"
            
            if dia not in horario_dict:
                horario_dict[dia] = []
                
            horario_dict[dia].append(franja)
            
        print(f"Horario final recuperado: {horario_dict}")
        return horario_dict
    except Exception as e:
        print(f"Error al cargar horario de BD: {e}")
        import traceback
        traceback.print_exc()
        return {}

def hay_solapamiento(franjas_existentes, nueva_franja):
    """Verifica si una nueva franja horaria se solapa con las existentes"""
    if not franjas_existentes:
        return False
        
    try:
        # Extraer horas de inicio y fin de la nueva franja
        inicio_nueva, fin_nueva = nueva_franja.split("-")
        hora_inicio_nueva = convertir_a_minutos(inicio_nueva)
        hora_fin_nueva = convertir_a_minutos(fin_nueva)
        
        # Verificar solapamiento con cada franja existente
        for franja in franjas_existentes:
            inicio_existente, fin_existente = franja.split("-")
            hora_inicio_existente = convertir_a_minutos(inicio_existente)
            hora_fin_existente = convertir_a_minutos(fin_existente)
            
            # Verificar si hay solapamiento
            if (hora_inicio_nueva < hora_fin_existente and 
                hora_fin_nueva > hora_inicio_existente):
                return True
        
        return False
    except Exception as e:
        logger.error(f"Error al verificar solapamiento: {e}")
        # En caso de error, considerar que hay solapamiento para prevenir
        return True

def convertir_a_minutos(hora_str):
    """Convierte una hora en formato HH:MM a minutos para facilitar comparaciones"""
    horas, minutos = map(int, hora_str.split(":"))
    return horas * 60 + minutos

def register_handlers(bot):
    """Registra los manejadores para la configuración de horarios"""
    
    @bot.message_handler(commands=['configurar_horario'])
    def configurar_horario(message):
        """Inicia el proceso de configuración del horario"""
        chat_id = message.chat.id
        
        # Verificar si es profesor
        try:
            user = get_user_by_telegram_id(chat_id)
            if not user or user['Tipo'].lower() != 'profesor':
                bot.send_message(chat_id, "⚠️ Solo los profesores pueden configurar horarios de tutoría.")
                return
        except Exception as e:
            logger.error(f"Error al verificar usuario: {e}")
            bot.send_message(chat_id, "❌ Error al verificar tus datos. Intenta más tarde.")
            return
        
        # Inicializar datos del usuario
        if chat_id not in user_data:
            user_data[chat_id] = {}
        
        # AQUÍ ES DONDE SE CARGA EL HORARIO
        # Usar la nueva función de carga con diagnóstico
        user_data[chat_id]['horario'] = cargar_horario_bd(chat_id)
    
        # Mostrar opciones de días de la semana
        markup = types.InlineKeyboardMarkup(row_width=2)
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        botones_dias = [types.InlineKeyboardButton(dia, callback_data=f"dia_{dia}") for dia in dias]
        markup.add(*botones_dias)
        markup.add(types.InlineKeyboardButton("💾 Guardar horario", callback_data="guardar_horario"))
        markup.add(types.InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_horario"))
        
        # Mostrar horario actual si existe
        if user_data[chat_id]['horario']:
            horario_formateado = formatear_horario_bonito(user_data[chat_id]['horario'])
            mensaje = f"Tu horario actual:\n\n{horario_formateado}\n\nSelecciona un día para configurar:"
        else:
            mensaje = "No tienes un horario configurado. Selecciona un día para comenzar:"
        
        bot.send_message(chat_id, mensaje, reply_markup=markup, parse_mode="Markdown")
        set_state(chat_id, SELECCIONANDO_DIA)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("dia_") and user_states.get(call.message.chat.id) == SELECCIONANDO_DIA)
    def handle_seleccion_dia(call):
        """Maneja la selección de un día de la semana"""
        chat_id = call.message.chat.id
        dia = call.data.split("_")[1]
        
        # Guardar el día seleccionado
        user_data[chat_id]["dia_actual"] = dia
        
        # Preparar mensaje y opciones para gestionar franjas horarias
        if dia in user_data[chat_id]["horario"] and user_data[chat_id]["horario"][dia]:
            franjas = user_data[chat_id]["horario"][dia]
            franjas_texto = "\n".join([f"• {franja}" for franja in franjas])
            mensaje = f"📅 *{dia}*\n\nFranjas horarias configuradas:\n{franjas_texto}\n\n¿Qué deseas hacer?"
        else:
            mensaje = f"📅 *{dia}*\n\nNo hay franjas horarias configuradas para este día.\n\n¿Qué deseas hacer?"
        
        # Botones para gestionar franjas
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ Añadir franja horaria", callback_data=f"add_franja_{dia}"),
            types.InlineKeyboardButton("🗑️ Eliminar franja horaria", callback_data=f"del_franja_{dia}"),
            types.InlineKeyboardButton("🔙 Volver a selección de días", callback_data="volver_dias")
        )
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=mensaje,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        set_state(chat_id, GESTION_FRANJAS)
        bot.answer_callback_query(call.id)
    
    @bot.callback_query_handler(func=lambda call: call.data == "volver_dias" and user_states.get(call.message.chat.id) in [GESTION_FRANJAS, POST_ANADIR_FRANJA])
    def handle_volver_dias(call):
        """Vuelve a la selección de días"""
        chat_id = call.message.chat.id
        
        # Mostrar opciones de días de la semana nuevamente
        markup = types.InlineKeyboardMarkup(row_width=2)
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        botones_dias = [types.InlineKeyboardButton(dia, callback_data=f"dia_{dia}") for dia in dias]
        markup.add(*botones_dias)
        markup.add(types.InlineKeyboardButton("💾 Guardar horario", callback_data="guardar_horario"))
        markup.add(types.InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_horario"))
        
        # Mostrar horario actual si existe
        if user_data[chat_id]['horario']:
            horario_formateado = formatear_horario_bonito(user_data[chat_id]['horario'])
            mensaje = f"Tu horario actual:\n\n{horario_formateado}\n\nSelecciona un día para configurar:"
        else:
            mensaje = "No tienes un horario configurado. Selecciona un día para comenzar:"
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=mensaje,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        set_state(chat_id, SELECCIONANDO_DIA)
        bot.answer_callback_query(call.id)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("add_franja_"))
    def handle_add_franja(call):
        """Maneja la adición de una nueva franja horaria"""
        chat_id = call.message.chat.id
        dia = call.data.split("_")[2]
        
        # Guardar el día actual
        user_data[chat_id]["dia_actual"] = dia
        
        # Solicitar la nueva franja horaria
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("🔙 Cancelar")
        
        bot.send_message(
            chat_id,
            f"Introduce la franja horaria para *{dia}* en formato HH:MM-HH:MM\n"
            "Por ejemplo: 09:00-11:00",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        set_state(chat_id, INTRODUCIR_FRANJA)
        bot.answer_callback_query(call.id)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("del_franja_"))
    def handle_del_franja(call):
        """Maneja la eliminación de una franja horaria"""
        chat_id = call.message.chat.id
        dia = call.data.split("_")[2]
        
        # Verificar que hay franjas para eliminar
        if dia not in user_data[chat_id]["horario"] or not user_data[chat_id]["horario"][dia]:
            bot.answer_callback_query(call.id, text="No hay franjas horarias para eliminar en este día")
            return
        
        # Mostrar botones para seleccionar la franja a eliminar
        markup = types.InlineKeyboardMarkup(row_width=1)
        for franja in user_data[chat_id]["horario"][dia]:
            markup.add(types.InlineKeyboardButton(franja, callback_data=f"eliminar_{dia}_{franja}"))
        
        # Añadir botón de volver con callback_data específico para este día
        markup.add(types.InlineKeyboardButton("🔙 Volver", callback_data=f"volver_gestion_{dia}"))
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"Selecciona la franja horaria a eliminar para *{dia}*:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)
    
    # Añadir este nuevo handler para manejar el botón volver desde la pantalla de eliminación
    @bot.callback_query_handler(func=lambda call: call.data.startswith("volver_gestion_"))
    def handle_volver_gestion(call):
        """Vuelve a la pantalla de gestión de franjas para un día específico"""
        chat_id = call.message.chat.id
        dia = call.data.split("_")[2]
        
        # Preparar mensaje y opciones para gestionar franjas horarias
        if dia in user_data[chat_id]["horario"] and user_data[chat_id]["horario"][dia]:
            franjas = user_data[chat_id]["horario"][dia]
            franjas_texto = "\n".join([f"• {franja}" for franja in franjas])
            mensaje = f"📅 *{dia}*\n\nFranjas horarias configuradas:\n{franjas_texto}\n\n¿Qué deseas hacer?"
        else:
            mensaje = f"📅 *{dia}*\n\nNo hay franjas horarias configuradas para este día.\n\n¿Qué deseas hacer?"
        
        # Botones para gestionar franjas
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ Añadir franja horaria", callback_data=f"add_franja_{dia}"),
            types.InlineKeyboardButton("🗑️ Eliminar franja horaria", callback_data=f"del_franja_{dia}"),
            types.InlineKeyboardButton("🔙 Volver a selección de días", callback_data="volver_dias")
        )
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=mensaje,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        set_state(chat_id, GESTION_FRANJAS)
        bot.answer_callback_query(call.id)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("eliminar_"))
    def handle_eliminar_franja(call):
        """Elimina una franja horaria específica"""
        chat_id = call.message.chat.id
        _, dia, hora = call.data.split("_", 2)
        
        try:
            # Eliminar la franja seleccionada
            user_data[chat_id]["horario"][dia].remove(hora)
            
            # Eliminar el día si no quedan franjas
            if not user_data[chat_id]["horario"][dia]:
                del user_data[chat_id]["horario"][dia]
            
            # Volver al menú de gestión usando la función handle_volver_gestion
            # Creamos un nuevo callback para simular el botón volver
            new_call = types.CallbackQuery(
                id=call.id,
                from_user=call.from_user,
                chat_instance=call.chat_instance,
                data=f"volver_gestion_{dia}",
                message=call.message
            )
            handle_volver_gestion(new_call)
            
            # Notificar que se eliminó correctamente
            bot.answer_callback_query(call.id, text=f"✅ Franja {hora} eliminada")
        except Exception as e:
            logger.error(f"Error al eliminar franja: {e}")
            bot.answer_callback_query(call.id, text="❌ Error al eliminar la franja")
    
    @bot.callback_query_handler(func=lambda call: call.data == "guardar_horario")
    def handle_guardar_horario(call):
        """Guarda el horario configurado en la base de datos"""
        chat_id = call.message.chat.id
        
        # Verificar que hay algo para guardar
        if not user_data[chat_id]["horario"]:
            bot.answer_callback_query(call.id, text="No has configurado ninguna franja horaria")
            return
        
        # Guardar el horario en la base de datos
        if guardar_horario_bd(chat_id, user_data[chat_id]["horario"]):
            horario_formateado = formatear_horario_bonito(user_data[chat_id]["horario"])
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"✅ *Cambios guardados*\n\nTu horario actualizado:\n\n{horario_formateado}",
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id, text="✅ Horario guardado correctamente")
            clear_state(chat_id)  # Limpiar estado para finalizar
        else:
            bot.answer_callback_query(call.id, text="❌ Error al guardar el horario")
    
    @bot.callback_query_handler(func=lambda call: call.data == "cancelar_horario")
    def handle_cancelar_horario(call):
        """Cancela la configuración del horario"""
        chat_id = call.message.chat.id
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="❌ Configuración de horario cancelada."
        )
        clear_state(chat_id)
        bot.answer_callback_query(call.id)
    
    @bot.message_handler(func=lambda m: user_states.get(m.chat.id) == INTRODUCIR_FRANJA)
    def handle_introducir_franja(message):
        """Procesa la introducción de una nueva franja horaria"""
        chat_id = message.chat.id
        texto = message.text.strip()
        dia = user_data[chat_id]["dia_actual"]
        
        # Cancelar la acción
        if texto == "🔙 Cancelar":
            # En lugar de crear manualmente un CallbackQuery, simplemente muestra
            # de nuevo las opciones del día seleccionado
            # Preparar mensaje y opciones para gestionar franjas horarias
            if dia in user_data[chat_id]["horario"] and user_data[chat_id]["horario"][dia]:
                franjas = user_data[chat_id]["horario"][dia]
                franjas_texto = "\n".join([f"• {franja}" for franja in franjas])
                mensaje = f"📅 *{dia}*\n\nFranjas horarias configuradas:\n{franjas_texto}\n\n¿Qué deseas hacer?"
            else:
                mensaje = f"📅 *{dia}*\n\nNo hay franjas horarias configuradas para este día.\n\n¿Qué deseas hacer?"
            
            # Botones para gestionar franjas
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("➕ Añadir franja horaria", callback_data=f"add_franja_{dia}"),
                types.InlineKeyboardButton("🗑️ Eliminar franja horaria", callback_data=f"del_franja_{dia}"),
                types.InlineKeyboardButton("🔙 Volver a selección de días", callback_data="volver_dias")
            )
            
            bot.send_message(
                chat_id,
                mensaje,
                reply_markup=markup,
                parse_mode="Markdown"
            )
            set_state(chat_id, GESTION_FRANJAS)
            return
        
        # Validar formato de la franja horaria
        if not re.match(r'^\d{1,2}:\d{2}-\d{1,2}:\d{2}$', texto):
            bot.send_message(
                chat_id,
                "⚠️ Formato incorrecto. Usa el formato HH:MM-HH:MM\n"
                "Ejemplo: 09:00-11:30",
                reply_markup=types.ReplyKeyboardRemove()
            )
            return
        
        try:
            # Validar horas y minutos
            inicio, fin = texto.split("-")
            hora_inicio, min_inicio = map(int, inicio.split(":"))
            hora_fin, min_fin = map(int, fin.split(":"))
            
            if not (0 <= hora_inicio <= 23 and 0 <= min_inicio <= 59):
                bot.send_message(
                    chat_id,
                    "⚠️ Hora de inicio inválida. Debe estar entre 00:00 y 23:59.",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return
                
            if not (0 <= hora_fin <= 23 and 0 <= min_fin <= 59):
                bot.send_message(
                    chat_id,
                    "⚠️ Hora de fin inválida. Debe estar entre 00:00 y 23:59.",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return
                
            if (hora_inicio > hora_fin) or (hora_inicio == hora_fin and min_inicio >= min_fin):
                bot.send_message(
                    chat_id,
                    "⚠️ La hora de inicio debe ser anterior a la hora de fin.",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return

            # Añadir la franja al día seleccionado
            if dia not in user_data[chat_id]["horario"]:
                user_data[chat_id]["horario"][dia] = []
                
            # Verificar que no exista esta franja para este día
            if texto in user_data[chat_id]["horario"][dia]:
                bot.send_message(
                    chat_id,
                    f"⚠️ Ya tienes configurada la franja {texto} para {dia}.\n"
                    "Por favor, introduce una franja horaria diferente.",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return
            
            # NUEVA VALIDACIÓN: Verificar solapamiento con horarios existentes
            if hay_solapamiento(user_data[chat_id]["horario"][dia], texto):
                bot.send_message(
                    chat_id,
                    f"⚠️ La franja {texto} se solapa con otro horario existente para {dia}.\n"
                    "Por favor, introduce una franja horaria que no se solape.",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                return
        
            # Añadir la franja al horario
            user_data[chat_id]["horario"][dia].append(texto)
            
            # Enviar confirmación y opciones
            bot.send_message(
                chat_id,
                f"✅ Franja {texto} añadida a {dia}",
                parse_mode="Markdown",
                reply_markup=types.ReplyKeyboardRemove()
            )
            
            # Opciones post-añadir
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("➕ Añadir otra franja", callback_data=f"add_franja_{dia}"),
                types.InlineKeyboardButton("🔙 Volver a selección de días", callback_data="volver_dias"),
                types.InlineKeyboardButton("💾 Guardar todo el horario", callback_data="guardar_horario")
            )
            
            bot.send_message(
                chat_id,
                "¿Qué deseas hacer ahora?",
                reply_markup=markup
            )
            
            set_state(chat_id, POST_ANADIR_FRANJA)
            
        except ValueError as e:
            bot.send_message(
                chat_id,
                f"⚠️ Error en el formato de hora: {e}",
                reply_markup=types.ReplyKeyboardRemove()
            )
            return

    @bot.message_handler(commands=['ver_horario'])
    def ver_horario(message):
        """Muestra el horario actual del profesor"""
        chat_id = message.chat.id
        
        # Verificar si es profesor
        try:
            user = get_user_by_telegram_id(chat_id)
            if not user:
                bot.send_message(chat_id, "⚠️ No se encontraron tus datos en el sistema.")
                return
        except Exception as e:
            logger.error(f"Error al verificar usuario: {e}")
            bot.send_message(chat_id, "❌ Error al verificar tus datos. Intenta más tarde.")
            return
        
        # Obtener el horario de la base de datos
        try:
            horario_str = user.get('Horario', '')
            
            if not horario_str:
                bot.send_message(chat_id, "No tienes un horario configurado. Usa /configurar_horario para establecerlo.")
                return
            
            # Convertir string a diccionario
            horario_dict = {}
            franjas = horario_str.split(',')
            for franja in franjas:
                franja = franja.strip()
                if ' ' in franja:
                    dia, hora = franja.split(' ', 1)
                    if dia not in horario_dict:
                        horario_dict[dia] = []
                    horario_dict[dia].append(hora)
            
            horario_formateado = formatear_horario_bonito(horario_dict)
            bot.send_message(chat_id, f"📅 *Tu horario de tutorías*\n\n{horario_formateado}", parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error al mostrar horario: {e}")
            bot.send_message(chat_id, "❌ Error al recuperar tu horario. Intenta más tarde.")

# Esta función debe ser llamada desde main.py
def setup_horarios_handlers(bot):
    register_handlers(bot)