import telebot
from telebot import types
import datetime
import sys
import os
import time

from handlers.horarios import set_state
from utils.state_manager import *

COMMAND_VALORAR_PROFESOR = 'valorar_profesor'
COMMAND_VER_VALORACIONES = 'ver_valoraciones'

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
VER_COMENTARIOS = "ver_comentarios"
VER_NO_ANONIMAS = "ver_no_anonimas"
VOLVER_VALORACIONES = "volver_valoraciones"

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
    def handle_valorar(call):
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
        user_id = get_usuarios(USUARIO_ID_TELEGRAM=chat_id)[0][USUARIO_ID]
        
        if opcion == SI:
            delete_valoracion(get_valoraciones(VALORACION_ID_EVALUADOR=user_id, VALORACION_ID_PROFESOR=profesor_id)[0][VALORACION_ID])
            handle_valorar(call)
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
        
    @bot.message_handler(commands=[COMMAND_VER_VALORACIONES])
    def handle_ver_valoraciones(message, get_text = False):
        """Muestra valoraciones recibidas"""
        chat_id = message.chat.id
        user = get_usuarios(USUARIO_ID_TELEGRAM=message.from_user.id)[0]

        # Verificar que el usuario es profesor
        if not user or user[USUARIO_TIPO] != USUARIO_TIPO_PROFESOR:
            bot.send_message(
                chat_id,
                "❌ Solo los profesores pueden versus valoraciones."
            )
            return

        valoraciones = get_valoraciones(VALORACION_ID_PROFESOR=user[USUARIO_ID])
        total = 0
        total_anon = 0
        total_public = 0
        n_anon = 0
        n_public = 0

        for val in valoraciones:
            total += val[VALORACION_PUNTUACION]
            if (val[VALORACION_ES_ANONIMA] == VALORACION_SI_ANONIMA):
                total_anon += val[VALORACION_PUNTUACION]
                n_anon += 1
            elif (val[VALORACION_ES_ANONIMA] == VALORACION_NO_ANONIMA):
                total_public += val[VALORACION_PUNTUACION]
                n_public += 1

        texto = "💯 Valoraciones (1-5⭐)\n\n"
            
            
        if valoraciones:
            texto += f"• Media total: {total/len(valoraciones)}⭐\n"
            if n_anon:
                texto += f"• Media anonimas: {total_anon/n_anon}⭐\n"
            else:
                texto += f"• Media anonimas: -⭐ (No hay)\n"
            if n_public:
                texto += f"• Media publicas: {total_public/n_public}⭐\n"
            else:
                texto += f"• Media publicas: -⭐ (No hay)\n"
        else:
            texto+= "No hay valoraciones"

        # Crear botones útiles con callback data simplificados
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(
                "📝 Ver comentarios",
                callback_data=VER_COMENTARIOS
            ),
            types.InlineKeyboardButton(
                "🧑 Ver nombres",
                callback_data=VER_NO_ANONIMAS
            )
        )

        # Enviar mensaje SIN formato markdown para evitar errores
        try:
            if not get_text:
                bot.send_message(
                    chat_id,
                    texto,
                    reply_markup=markup
                )
            else:
                return texto, markup
        except Exception as e:
            print(f"Error al mostrar valoraciones: {e}")
            bot.send_message(
                chat_id,
                "❌ Error al mostrar valoraciones.",
                reply_markup=markup
            )
        
    @bot.callback_query_handler(func=lambda call: call.data.startswith(VER_COMENTARIOS))
    def handle_ver_no_anonimas(call):
        chat_id = call.message.chat.id
        user = get_usuarios(USUARIO_ID_TELEGRAM=chat_id)[0]
        valoraciones = get_valoraciones(VALORACION_ID_PROFESOR=user[USUARIO_ID])

        texto = "💯 Valoraciones comentadas (1-5⭐)\n\n"

        hay_comentadas = False
        if valoraciones and valoraciones != []:
            for val in valoraciones:
                if val[VALORACION_COMENTARIO]:
                    hay_comentadas = True
                    alumno = get_usuarios(USUARIO_ID=val[VALORACION_ID_EVALUADOR])[0]

                    if val[VALORACION_ES_ANONIMA] == VALORACION_SI_ANONIMA:
                        texto+= "• Anonimo: "
                    elif val[VALORACION_ES_ANONIMA] == VALORACION_NO_ANONIMA:
                        texto+= f"• {alumno[USUARIO_NOMBRE]} {alumno[USUARIO_APELLIDOS]}: "
                    
                    texto += (f"{val[VALORACION_PUNTUACION]}⭐\n"

                              f"   {val[VALORACION_COMENTARIO]}\n\n"         
                    )
            
            if (hay_comentadas == False):
                texto += "No hay valoraciones\n"
        else:
            texto += "No hay valoraciones\n"

        # Botón para volver
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔙 Volver", callback_data=VOLVER_VALORACIONES))
        print("✅ Markup de botones creado")
        
        bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=texto,
                reply_markup=markup,
                parse_mode="Markdown"
            )

        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith(VER_NO_ANONIMAS))
    def handle_ver_no_anonimas(call):
        chat_id = call.message.chat.id
        user = get_usuarios(USUARIO_ID_TELEGRAM=chat_id)[0]
        valoraciones = get_valoraciones(VALORACION_ID_PROFESOR=user[USUARIO_ID], VALORACION_ES_ANONIMA=VALORACION_NO_ANONIMA)

        texto = "💯 Valoraciones publicas (1-5⭐)\n\n"

        if valoraciones and valoraciones != []:
            valoraciones = sorted(valoraciones, key=lambda val: val[VALORACION_PUNTUACION])
            current_score = 0
            for val in valoraciones:
                if current_score < val[VALORACION_PUNTUACION]:
                    current_score = val[VALORACION_PUNTUACION]
                    texto += f"• " + current_score*"⭐" + f"({current_score}):\n"

                alumno = get_usuarios(USUARIO_ID=val[VALORACION_ID_EVALUADOR])[0]
                texto+= f"  -{alumno[USUARIO_NOMBRE]} {alumno[USUARIO_APELLIDOS]}\n"
        else:
            texto += "No hay valoraciones publicas\n"

        # Botón para volver
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔙 Volver", callback_data=VOLVER_VALORACIONES))
        print("✅ Markup de botones creado")
        
        bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=texto,
                reply_markup=markup,
                parse_mode="Markdown"
            )

        bot.answer_callback_query(call.id)

    
    @bot.callback_query_handler(func=lambda call: call.data.startswith(VOLVER_VALORACIONES))
    def handle_volver_valoraciones(call):
        chat_id = call.message.chat.id
        user = get_usuarios(USUARIO_ID_TELEGRAM=chat_id)[0]
        class SimpleMessage:
                def __init__(self, chat_id, user_id, text):
                    self.chat = types.Chat(chat_id, 'private')
                    self.from_user = types.User(user_id, False, 'Usuario')
                    self.text = text

        # Crear el mensaje simplificado
        msg = SimpleMessage(chat_id, user[USUARIO_ID_TELEGRAM], f'/{COMMAND_VER_VALORACIONES}')
        
        texto, markup = handle_ver_valoraciones(msg,True)

        bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=texto,
                reply_markup=markup,
                parse_mode="Markdown"
            )
        

    
