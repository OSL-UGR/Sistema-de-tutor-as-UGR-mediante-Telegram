import os
import logging
import dict2xml
from telebot import types

from handlers.commands import COMMAND_VER_MENSAJES, COMMAND_VER_REACCIONES
from db.queries import get_asignaturas, get_matriculas, get_mensajes, get_usuarios, get_reacciones
from db.constantes import *

MENSAJES = "mensajes_"

# Configuración del logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='logs/horarios.log')


def register_handlers(bot):
    @bot.message_handler(commands=[COMMAND_VER_REACCIONES])
    def handle_ver_reacciones(message):
        """Muestra reacciones recibidas o puestas"""
        chat_id = message.chat.id
        user = get_usuarios(USUARIO_ID_TELEGRAM=message.from_user.id)
        texto = ""

        # Verificar que el usuario es profesor
        if user and user[0][USUARIO_TIPO] == USUARIO_TIPO_PROFESOR:
            user = user[0]
            reacciones = get_reacciones(REACCION_ID_PROFESOR=user[USUARIO_ID])
            reacciones.sort(key=lambda x: (x[REACCION_ID_ASIGNATURA], x[REACCION_ID_ALUMNO]))
            
            if reacciones:
                texto = "❤️ Reacciones puestas:\n\n"
                last_alumno = None
                last_asignatura = None
                for reaccion in reacciones:
                    if last_asignatura != reaccion[REACCION_ID_ASIGNATURA]:
                        if last_asignatura is not None:
                            texto += "\n"
                        last_asignatura = reaccion[REACCION_ID_ASIGNATURA]
                        last_alumno = None
                        asignatura = get_asignaturas(ASIGNATURA_ID=reaccion[REACCION_ID_ASIGNATURA])
                        if asignatura:
                            texto += f"📚 Asignatura: {asignatura[0][ASIGNATURA_NOMBRE]}\n"
                    if last_alumno != reaccion[REACCION_ID_ALUMNO]:
                        if last_alumno is not None:
                            texto += "\n"
                        last_alumno = reaccion[REACCION_ID_ALUMNO]
                        alumno = get_usuarios(USUARIO_ID=last_alumno)
                        if alumno:
                            texto += f"    👤 Alumno: {alumno[0][USUARIO_NOMBRE]} {alumno[0][USUARIO_APELLIDOS]}\n"
                    texto += f"        • {reaccion[REACCION_EMOJI]} - {reaccion[REACCION_CANTIDAD]}\n"
            else:
                texto = "❌ No tienes reacciones recibidas."

        elif user and user[0][USUARIO_TIPO] == USUARIO_TIPO_ESTUDIANTE:
            user = user[0]
            reacciones = get_reacciones(REACCION_ID_ALUMNO=user[USUARIO_ID])
            reacciones.sort(key=lambda x: (x[REACCION_ID_ASIGNATURA], x[REACCION_ID_PROFESOR]))
            
            if reacciones:
                texto = "❤️ Reacciones recibidas:\n\n"
                last_profesor = None
                last_asignatura = None
                for reaccion in reacciones:
                    if last_asignatura != reaccion[REACCION_ID_ASIGNATURA]:
                        if last_asignatura is not None:
                            texto += "\n"
                        last_asignatura = reaccion[REACCION_ID_ASIGNATURA]
                        last_profesor = None
                        asignatura = get_asignaturas(ASIGNATURA_ID=reaccion[REACCION_ID_ASIGNATURA])
                        if asignatura:
                            texto += f"📚 Asignatura: {asignatura[0][ASIGNATURA_NOMBRE]}\n"
                    if last_profesor != reaccion[REACCION_ID_PROFESOR]:
                        if last_profesor is not None:
                            texto += "\n"
                        last_profesor = reaccion[REACCION_ID_PROFESOR]
                        profesor = get_usuarios(USUARIO_ID=last_profesor)
                        if profesor:
                            texto += f"    👤 Profesor: {profesor[0][USUARIO_NOMBRE]} {profesor[0][USUARIO_APELLIDOS]}\n"
                    texto += f"        • {reaccion[REACCION_EMOJI]} - {reaccion[REACCION_CANTIDAD]}\n"
            else:
                texto = "❌ No tienes reacciones recibidas."
        else:
            texto = "❌ No tienes permisos para ver reacciones."

        # Enviar mensaje SIN formato markdown para evitar errores
        try:
            bot.send_message(
                chat_id,
                texto,
            )
        except Exception as e:
            print(f"Error al mostrar reacciones: {e}")
            bot.send_message(
                chat_id,
                "❌ Error al mostrar reacciones.",
            )

    @bot.message_handler(commands=[COMMAND_VER_MENSAJES])
    def handle_ver_mensajes(message):
        chat_id = message.chat.id
        user_id = message.from_user.id
        profesor = get_usuarios(USUARIO_ID_TELEGRAM=user_id)
        texto = None
        markup = None

        # Verificar que el usuario es profesor
        if profesor and profesor[0][USUARIO_TIPO] == USUARIO_TIPO_PROFESOR:
            profesor = profesor[0]
            texto = f"📩 Selecciona la asignatura de la que quieras el historial de mensajes:\n\n"
            matriculas = get_matriculas(MATRICULA_ID_USUARIO=profesor[USUARIO_ID])
            markup = types.InlineKeyboardMarkup()

            callback_data = f"{MENSAJES}1"
            markup.add(types.InlineKeyboardButton(text="Tutorias", callback_data=callback_data))

            if matriculas:
                for asig in matriculas:
                    callback_data = f"{MENSAJES}{asig[MATRICULA_ID_ASIGNATURA]}"
                    markup.add(types.InlineKeyboardButton(text=asig[MATRICULA_ASIGNATURA], callback_data=callback_data))
            
            
        # Enviar mensaje SIN formato markdown para evitar errores
        try:
            bot.send_message(
                chat_id,
                texto if texto else "❌ Solo profesores pueden ver mensajes.",
                reply_markup=markup,
            )
        except Exception as e:
            print(f"Error al mostrar reacciones: {e}")
            bot.send_message(
                chat_id,
                "❌ Error al mostrar mensajes.",
            )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith(MENSAJES))
    def handle_configuracion_asignatura(call):
        user_id = call.from_user.id
        id_asignatura = call.data.split('_')[1]  # Extraer ID de la asignatura

        profesor = get_usuarios(USUARIO_ID_TELEGRAM=user_id)

        if not profesor or profesor[0][USUARIO_TIPO] != USUARIO_TIPO_PROFESOR:
            bot.answer_callback_query(call.id, "❌ Solo profesores pueden ver mensajes.")
            return
        
        profesor = profesor[0]

        mensajes = get_mensajes(MENSAJE_ID_ASIGNATURA=id_asignatura, MENSAJE_ID_PROFESOR=profesor[USUARIO_ID])
        asignatura = get_asignaturas(ASIGNATURA_ID=id_asignatura)[0]
        mensajes_dict = {}

        if not mensajes:
            bot.answer_callback_query(call.id, "❌ No hay mensajes para esta asignatura.")
            return

        mensajes.sort(key=lambda x: x[MENSAJE_FECHA])
        texto = f"📩 Historial de mensajes para la asignatura:\n\n"
        for mensaje in mensajes:
            if mensaje[MENSAJE_ID_CHAT] not in mensajes_dict:
                mensajes_dict[mensaje[MENSAJE_ID_CHAT]] = {}

            mensajes_dict[mensaje[MENSAJE_ID_CHAT]][f"M_{mensaje[MENSAJE_ID_TELEGRAM]}"] = {
                "ID Mensaje": mensaje[MENSAJE_ID_TELEGRAM],
                "Fecha": mensaje[MENSAJE_FECHA],
                "ID Usuario": "No registrado",
                "Nombre": "No registrado",
                "Texto": mensaje[MENSAJE_TEXTO],
            }
            usuario = get_usuarios(USUARIO_ID=mensaje[MENSAJE_ID_SENDER])
            if usuario:
                usuario = usuario[0]
                mensajes_dict[mensaje[MENSAJE_ID_CHAT]][f"M_{mensaje[MENSAJE_ID_TELEGRAM]}"]["ID Usuario"] = usuario[USUARIO_ID_TELEGRAM]
                mensajes_dict[mensaje[MENSAJE_ID_CHAT]][f"M_{mensaje[MENSAJE_ID_TELEGRAM]}"]["Nombre"] = f"{usuario[USUARIO_NOMBRE]} {usuario[USUARIO_APELLIDOS]}"
        # Enviar mensaje SIN formato markdown para evitar errores
        try:
            
            data_sorter = dict2xml.DataSorter.never()
            xml = dict2xml.dict2xml(mensajes_dict, wrap=asignatura[ASIGNATURA_NOMBRE], data_sorter=data_sorter)

            ruta_xml = f"./tmp/mensajes_{asignatura[ASIGNATURA_NOMBRE]}_{profesor[USUARIO_NOMBRE]}_{profesor[USUARIO_APELLIDOS]}.xml"
            xmlfile = open(ruta_xml, "w")
            xmlfile.write(xml)
            xmlfile.close()

            
            xmlfile = open(ruta_xml, "rb")
            bot.send_document(
                call.message.chat.id,
                xmlfile,
                caption=texto,
            )
            xmlfile.close()

            os.remove(ruta_xml)

            bot.delete_message(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
            )
            
        except Exception as e:
            print(f"❌ Error al procesar mensajes: {e}")
            bot.edit_message_text(
                "❌ Error al procesar mensajes.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="Markdown"
            )
