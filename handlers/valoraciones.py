import telebot
from telebot import types
import datetime
import sys
import os
import time

from handlers.horarios import set_state
from utils.state_manager import *

COMMAND_VALORAR_PROFESOR = 'valorar_profesor'

# Estados

ESCRIBIENDO_COMENTARIO = "escribiendo_comentario"

# Calldata
VALORAR = "valorar_"
SOBREESCRIBIR = "sobreescribir_"
PUNTOS = "puntos_"
COMENTARIO = "comentario_"
ANONIMO = "anonimo_"
SI = "si"
NO = "no"

# Añadir directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.queries import delete_valoracion, get_matriculas, get_usuarios_by_multiple_ids, get_valoraciones, insert_valoracion, get_usuarios
from db.constantes import *

def register_handlers(bot):
    """Registra todos los handlers relacionados con valoraciones"""
    
    @bot.message_handler(commands=[COMMAND_VALORAR_PROFESOR])
    def handle_valorar_profesor(message):
        """Maneja el comando para valorar a un profesor"""
        chat_id = message.chat.id
        user = get_usuarios(USUARIO_ID_TELEGRAM=message.from_user.id)[0]
        
        if not user:
            bot.send_message(
                chat_id,
                "❌ No estás registrado. Usa /start para registrarte."
            )
            return
            
        if user[USUARIO_TIPO] != USUARIO_TIPO_ESTUDIANTE:
            bot.send_message(
                chat_id,
                "❌ Solo los estudiantes pueden valorar a profesores."
            )
            return
        
        # Buscar profesores disponibles para valorar        
        # Obtener profesores de las asignaturas del estudiante
        matriculas = get_matriculas(MATRICULA_ID_USUARIO=user[USUARIO_ID])
        ids_asignaturas = []
        
        for matricula in matriculas:
            ids_asignaturas.append(matricula[MATRICULA_ID_ASIGNATURA])

        matriculas_profesores = get_matriculas(MATRICULA_TIPO=MATRICULA_PROFESOR)
        ids_profesores = []

        for matricula in matriculas_profesores:
            if matricula[MATRICULA_ID_ASIGNATURA] in ids_asignaturas:
                ids_profesores.append(matricula[MATRICULA_ID_USUARIO])
        
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
                text=prof[USUARIO_NOMBRE],
                callback_data=f"{VALORAR}{prof[USUARIO_ID]}"
            ))
        
        bot.send_message(
            chat_id,
            "👨‍🏫 *Valorar profesor*\n\n"
            "Selecciona el profesor que quieres valorar:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith(VALORAR))
    def handle_seleccion_profesor_valoracion(call):
        chat_id = call.message.chat.id
        profesor_id = int(call.data.split("_")[1])
        user_id = get_usuarios(USUARIO_ID_TELEGRAM=chat_id)[0][GRUPO_ID_USUARIO]
        
        profesor = get_usuarios(USUARIO_ID=profesor_id)[0]
        valoracion_actual = get_valoraciones(VALORACION_ID_EVALUADOR=user_id, VALORACION_ID_PROFESOR=profesor_id)

        if valoracion_actual != []:
            # Ya has valorado a ese profesor
            valoracion_actual = valoracion_actual[0]
            markup = types.InlineKeyboardMarkup(row_width=2)
            buttons = [
                types.InlineKeyboardButton("Si", callback_data=f"{SOBREESCRIBIR}{profesor_id}_{SI}"),
                types.InlineKeyboardButton("No", callback_data=f"{SOBREESCRIBIR}{profesor_id}_{NO}"),
            ]
            markup.add(*buttons)

            texto = f"Ya has valorado a: *{profesor[USUARIO_NOMBRE]}* con {valoracion_actual[VALORACION_PUNTUACION]}⭐\n"
            if (valoracion_actual[VALORACION_COMENTARIO]):
                texto +=f"Y comentario: {valoracion_actual[VALORACION_COMENTARIO]}\n"
            texto += "\n¿Quieres sobreescribir esta valoración?"

            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=texto,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        else:
            # Obtener datos del profesor
            user_data[chat_id] = {PROFESOR_ID: profesor_id, PROFESOR_NOMBRE: profesor[USUARIO_NOMBRE]}

            # Solicitar puntuación
            markup = types.InlineKeyboardMarkup(row_width=5)
            buttons = [
                types.InlineKeyboardButton("1⭐", callback_data=f"{PUNTOS}1"),
                types.InlineKeyboardButton("2⭐", callback_data=f"{PUNTOS}2"),
                types.InlineKeyboardButton("3⭐", callback_data=f"{PUNTOS}3"),
                types.InlineKeyboardButton("4⭐", callback_data=f"{PUNTOS}4"),
                types.InlineKeyboardButton("5⭐", callback_data=f"{PUNTOS}5")
            ]
            markup.add(*buttons)

            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"Vas a valorar a: *{profesor[USUARIO_NOMBRE]}*\n\n¿Qué puntuación le darías del 1 al 5?",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith(SOBREESCRIBIR))
    def handle_sobreescribir(call):
        chat_id = call.message.chat.id
        profesor_id = call.data.split("_")[1]
        opcion = call.data.split("_")[2]
        user_id = get_usuarios(USUARIO_ID_TELEGRAM=chat_id)[0][GRUPO_ID_USUARIO]
        
        if opcion == SI:
            delete_valoracion(get_valoraciones(VALORACION_ID_EVALUADOR=user_id, VALORACION_ID_PROFESOR=profesor_id)[0][VALORACION_ID])
            handle_seleccion_profesor_valoracion(call)
        else:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="✅ Ok, valoracion cancelada"
            )
        
        bot.answer_callback_query(call.id)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith(PUNTOS))
    def handle_puntuacion_profesor(call):
        chat_id = call.message.chat.id
        puntuacion = int(call.data.split("_")[1])
        
        user_data[chat_id][PUNTUACION] = puntuacion
        
        # Preguntar si desea dejar un comentario
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Sí", callback_data=f"{COMENTARIO}{SI}"),
            types.InlineKeyboardButton("No", callback_data=f"{COMENTARIO}{NO}")
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
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith(COMENTARIO))
    def handle_opcion_comentario(call):
        chat_id = call.message.chat.id
        opcion = call.data.split("_")[1]
        
        if opcion == SI:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text="Por favor, escribe tu comentario sobre el profesor:"
            )
            set_state(chat_id, ESCRIBIENDO_COMENTARIO)
            user_data[chat_id][MENSAJE_ID] = call.message.message_id
        else:
            # No quiere dejar comentario, preguntar si valoración anónima
            preguntar_valoracion_anonima(chat_id, bot, call)
        
        bot.answer_callback_query(call.id)
    
    @bot.message_handler(func=lambda message: get_state(message.chat.id) == ESCRIBIENDO_COMENTARIO)
    def handle_comentario_profesor(message):
        chat_id = message.chat.id
        comentario = message.text.strip()
        
        user_data[chat_id][COMENTARIO] = comentario

        bot.delete_message(chat_id, message.id)
        
        # Preguntar si valoración anónima
        preguntar_valoracion_anonima(chat_id, bot)
    
    def preguntar_valoracion_anonima(chat_id, bot, call=None):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Sí, anónima", callback_data=f"{ANONIMO}{SI}"),
            types.InlineKeyboardButton("No, mostrar mi nombre", callback_data=f"{ANONIMO}{NO}")
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
                message_id=user_data[chat_id][MENSAJE_ID],
                text="¿Deseas que tu valoración sea anónima?\n\nSi eliges 'No', el profesor podrá ver tu nombre.",
                reply_markup=markup
            )
            del user_data[chat_id][MENSAJE_ID]
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith(ANONIMO))
    def handle_opcion_anonima(call):
        chat_id = call.message.chat.id
        es_anonimo = 1 if call.data == f"{ANONIMO}{SI}" else 0
        
        
        # Guardar valoración en la base de datos
        try:
            evaluador_id = get_usuarios(USUARIO_ID_TELEGRAM=call.from_user.id)[0][USUARIO_ID]
            profesor_id = user_data[chat_id][PROFESOR_ID]
            puntuacion = user_data[chat_id][PUNTUACION]
            comentario = user_data[chat_id].get(COMENTARIO, "")
            fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            insert_valoracion(evaluador_id, profesor_id, puntuacion, comentario, fecha, es_anonimo, user_data[chat_id].get(GRUPO_ID))
            
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=f"✅ ¡Valoración guardada correctamente!\n\n"
                +f"Has valorado a *{user_data[chat_id][PROFESOR_NOMBRE]}* con "
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
def iniciar_valoracion_profesor(bot, profesor_id, estudiante_id, grupo_id=None):
    """Inicia el proceso de valoración de un profesor desde otro módulo"""
    # Buscar usuario por id
    estudiante = get_usuarios(USUARIO_ID=estudiante_id)[0]
    
    # Si no hay TelegramID, no podemos enviar mensaje
    if not estudiante or not estudiante.get(USUARIO_ID_TELEGRAM):
        return False
    
    chat_id = estudiante[USUARIO_ID_TELEGRAM]
    
    # Obtener datos del profesor
    profesor = get_usuarios(USUARIO_ID=profesor_id)[0]
    
    if not profesor:
        bot.send_message(chat_id, "❌ Profesor no encontrado")
        return False
    
    # Guardar datos para el flujo de valoración
    user_data[chat_id] = {
        PROFESOR_ID: profesor_id, 
        PROFESOR_NOMBRE: profesor[USUARIO_NOMBRE],
        ESTUDIANTE_ID: estudiante_id,
        GRUPO_ID: grupo_id
    }
    
    # Mostrar opciones de valoración (con estrellas)
    markup = types.InlineKeyboardMarkup(row_width=1)
    buttons = [
        types.InlineKeyboardButton("⭐", callback_data="{PUNTOS}1"),
        types.InlineKeyboardButton("⭐⭐", callback_data="{PUNTOS}2"),
        types.InlineKeyboardButton("⭐⭐⭐", callback_data="{PUNTOS}3"),
        types.InlineKeyboardButton("⭐⭐⭐⭐", callback_data="{PUNTOS}4"),
        types.InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="{PUNTOS}5")
    ]
    markup.add(*buttons)
    
    # Enviar nuevo mensaje
    bot.edit_message_text(
        chat_id=chat_id,
        text=f"Vas a valorar la tutoría con: *{profesor[USUARIO_NOMBRE]}*\n\n¿Qué puntuación le darías?",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    
    return True