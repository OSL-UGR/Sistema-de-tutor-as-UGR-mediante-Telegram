import telebot
from telebot import types
import datetime
import sys
import os
import time

from handlers.horarios import set_state
from utils.state_manager import clear_state, get_state, user_data

# Añadir directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.queries import get_matriculas, get_usuarios_by_multiple_ids, insert_valoracion, get_usuarios

def register_handlers(bot):
    """Registra todos los handlers relacionados con valoraciones"""
    
    @bot.message_handler(commands=['valorar_profesor'])
    def handle_valorar_profesor(message):
        """Maneja el comando para valorar a un profesor"""
        chat_id = message.chat.id
        user = get_usuarios(TelegramID=message.from_user.id)[0]
        
        if not user:
            bot.send_message(
                chat_id,
                "❌ No estás registrado. Usa /start para registrarte."
            )
            return
            
        if user['Tipo'] != 'estudiante':
            bot.send_message(
                chat_id,
                "❌ Solo los estudiantes pueden valorar a profesores."
            )
            return
        
        # Buscar profesores disponibles para valorar        
        # Obtener profesores de las asignaturas del estudiante
        matriculas = get_matriculas(Id_usuario=user['Id_usuario'])
        ids_asignaturas = []
        
        for matricula in matriculas:
            ids_asignaturas.append(matricula['Id_asignatura'])

        matriculas_profesores = get_matriculas(Tipo="docente")
        ids_profesores = []

        for matricula in matriculas_profesores:
            if matricula['Id_asignatura'] in ids_asignaturas:
                ids_profesores.append(matricula['Id_usuario'])
        
        profesores = get_usuarios_by_multiple_ids(ids_profesores)
        
        if not profesores:
            bot.send_message(
                chat_id,
                "❌ No se encontraron profesores para valorar.\n"
                "Debes estar matriculado en asignaturas con profesores."
            )
            return
        
        # Mostrar lista de profesores
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for prof in profesores:
            markup.add(types.InlineKeyboardButton(
                text=prof['Nombre'],
                callback_data=f"valorar_{prof['Id_usuario']}"
            ))
        
        bot.send_message(
            chat_id,
            "👨‍🏫 *Valorar profesor*\n\n"
            "Selecciona el profesor que quieres valorar:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("valorar_"))
    def handle_seleccion_profesor_valoracion(call):
        chat_id = call.message.chat.id
        profesor_id = int(call.data.split("_")[1])
        
        # Obtener datos del profesor
        profesor = get_usuarios(Id_usuario=profesor_id)[0]
        
        user_data[chat_id] = {"profesor_id": profesor_id, "profesor_nombre": profesor['Nombre']}
        
        # Solicitar puntuación
        markup = types.InlineKeyboardMarkup(row_width=5)
        buttons = [
            types.InlineKeyboardButton("1⭐", callback_data="puntos_1"),
            types.InlineKeyboardButton("2⭐", callback_data="puntos_2"),
            types.InlineKeyboardButton("3⭐", callback_data="puntos_3"),
            types.InlineKeyboardButton("4⭐", callback_data="puntos_4"),
            types.InlineKeyboardButton("5⭐", callback_data="puntos_5")
        ]
        markup.add(*buttons)
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"Vas a valorar a: *{profesor['Nombre']}*\n\n¿Qué puntuación le darías del 1 al 5?",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        bot.answer_callback_query(call.id)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("puntos_"))
    def handle_puntuacion_profesor(call):
        chat_id = call.message.chat.id
        puntuacion = int(call.data.split("_")[1])
        
        user_data[chat_id]["puntuacion"] = puntuacion
        
        # Preguntar si desea dejar un comentario
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Sí", callback_data="comentario_si"),
            types.InlineKeyboardButton("No", callback_data="comentario_no")
        )
        
        # Mostramos las estrellas de forma visual
        estrellas = "⭐" * puntuacion
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"Has dado una puntuación de {estrellas}\n\n¿Deseas añadir un comentario adicional?",
            reply_markup=markup
        )
        
        bot.answer_callback_query(call.id)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("comentario_"))
    def handle_opcion_comentario(call):
        chat_id = call.message.chat.id
        opcion = call.data.split("_")[1]
        
        if opcion == "si":
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="Por favor, escribe tu comentario sobre el profesor:"
            )
            set_state(chat_id, "escribiendo_comentario")
            user_data[chat_id]["id_mensaje"] = call.message.message_id
        else:
            # No quiere dejar comentario, preguntar si valoración anónima
            preguntar_valoracion_anonima(chat_id, bot, call)
        
        bot.answer_callback_query(call.id)
    
    @bot.message_handler(func=lambda message: get_state(message.chat.id) == "escribiendo_comentario")
    def handle_comentario_profesor(message):
        chat_id = message.chat.id
        comentario = message.text.strip()
        
        user_data[chat_id]["comentario"] = comentario

        bot.delete_message(chat_id, message.id)
        
        # Preguntar si valoración anónima
        preguntar_valoracion_anonima(chat_id, bot)
    
    def preguntar_valoracion_anonima(chat_id, bot, call=None):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Sí, anónima", callback_data="anonimo_si"),
            types.InlineKeyboardButton("No, mostrar mi nombre", callback_data="anonimo_no")
        )
        if call is not None:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="¿Deseas que tu valoración sea anónima?\n\nSi eliges 'No', el profesor podrá ver tu nombre.",
                reply_markup=markup
            )
        else:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=user_data[chat_id]["id_mensaje"],
                text="¿Deseas que tu valoración sea anónima?\n\nSi eliges 'No', el profesor podrá ver tu nombre.",
                reply_markup=markup
            )
            del user_data[chat_id]["id_mensaje"]
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("anonimo_"))
    def handle_opcion_anonima(call):
        chat_id = call.message.chat.id
        es_anonimo = 1 if call.data == "anonimo_si" else 0
        
        user_data[chat_id]["es_anonimo"] = es_anonimo
        
        # Guardar valoración en la base de datos
        try:
            evaluador_id = get_usuarios(TelegramID=call.from_user.id)[0]['Id_usuario']
            profesor_id = user_data[chat_id]["profesor_id"]
            puntuacion = user_data[chat_id]["puntuacion"]
            comentario = user_data[chat_id].get("comentario", "")
            fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            insert_valoracion(evaluador_id, profesor_id, puntuacion, comentario, fecha, es_anonimo, user_data[chat_id].get("sala_id"))
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"✅ ¡Valoración guardada correctamente!\n\n"
                +f"Has valorado a *{user_data[chat_id]['profesor_nombre']}* con "
                +f"{puntuacion} estrellas.\n\n"
                +"Gracias por tu feedback.",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            bot.send_message(
                chat_id,
                f"❌ Error al guardar la valoración: {str(e)}"
            )
        
        finally:
            clear_state(chat_id)
        
        bot.answer_callback_query(call.id)
        
# Al final del archivo, añade esta función para que sea importable desde otros módulos
def iniciar_valoracion_profesor(bot, profesor_id, estudiante_id, sala_id=None):
    """Inicia el proceso de valoración de un profesor desde otro módulo"""
    # Buscar usuario por id
    estudiante = get_usuarios(Id_usuario=estudiante_id)[0]
    
    # Si no hay TelegramID, no podemos enviar mensaje
    if not estudiante or not estudiante.get('TelegramID'):
        return False
    
    chat_id = estudiante['TelegramID']
    
    # Obtener datos del profesor
    profesor = get_usuarios(Id_usuario=profesor_id)[0]
    
    if not profesor:
        bot.send_message(chat_id, "❌ Profesor no encontrado")
        return False
    
    # Guardar datos para el flujo de valoración
    user_data[chat_id] = {
        "profesor_id": profesor_id, 
        "profesor_nombre": profesor['Nombre'],
        "estudiante_id": estudiante_id,
        "sala_id": sala_id
    }
    
    # Mostrar opciones de valoración (con estrellas)
    markup = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        types.InlineKeyboardButton("⭐", callback_data="puntos_1"),
        types.InlineKeyboardButton("⭐⭐", callback_data="puntos_2"),
        types.InlineKeyboardButton("⭐⭐⭐", callback_data="puntos_3"),
        types.InlineKeyboardButton("⭐⭐⭐⭐", callback_data="puntos_4"),
        types.InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="puntos_5")
    ]
    markup.add(*buttons)
    
    # Enviar nuevo mensaje
    bot.edit_message_text(
        chat_id=chat_id,
        text=f"Vas a valorar la tutoría con: *{profesor['Nombre']}*\n\n¿Qué puntuación le darías?",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    
    return True