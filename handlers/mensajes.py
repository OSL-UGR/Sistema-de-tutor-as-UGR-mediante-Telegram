from collections import defaultdict
import os
import logging
import dict2xml
from pyparsing import Dict
from telebot import types

from handlers.commands import COMMAND_VER_MENSAJES, COMMAND_VER_REACCIONES
from db.queries import get_asignaturas, get_matriculas_asignatura_de_usuario, get_mensajes, get_usuarios, get_reacciones, get_usuarios_local
from db.constantes import *
from utils.state_manager import user_data

MENSAJES = "mensajes_"

# Configuración del logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='logs/horarios.log')


def register_handlers(bot):
    @bot.message_handler(commands=[COMMAND_VER_REACCIONES])
    def handle_ver_reacciones(message):
        """Muestra reacciones recibidas o puestas"""
        chat_id = message.chat.id
        user = get_usuarios_local(USUARIO_ID_TELEGRAM=message.from_user.id)
        texto = ""

        user_data[chat_id] = defaultdict(dict)  # Inicializar el diccionario para este chat

        # Verificar que el usuario es profesor
        if user and user[0][USUARIO_TIPO] == USUARIO_TIPO_PROFESOR:
            user = user[0]
            reacciones = get_reacciones(REACCION_ID_PROFESOR=user[USUARIO_ID])
            reacciones.sort(key=lambda x: (x[REACCION_ID_ASIGNATURA], x[REACCION_ID_ALUMNO]))
            matriculas = get_matriculas_asignatura_de_usuario(MATRICULA_ID_USUARIO=user[USUARIO_ID], MATRICULA_TIPO=MATRICULA_TODAS)
            
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
                        if reaccion[REACCION_ID_ASIGNATURA] != 1:
                            matricula = next((item for item in matriculas if (item[MATRICULA_ID_ASIGNATURA] == reaccion[REACCION_ID_ASIGNATURA] )), None)
                        else:
                            matricula = {
                                MATRICULA_ASIGNATURA_NOMBRE_CORTO:"Tutoria"
                            }
                        if matricula:
                            texto += f"📚 Asignatura: {matricula[MATRICULA_ASIGNATURA_NOMBRE_CORTO]}\n"
                    if last_alumno != reaccion[REACCION_ID_ALUMNO]:
                        if last_alumno is not None:
                            texto += "\n"
                        last_alumno = reaccion[REACCION_ID_ALUMNO]
                        
                        matricula = next((item for item in matriculas if (item[MATRICULA_ID_USUARIO] == reaccion[REACCION_ID_PROFESOR])),None)
                        if matricula:
                            texto += f"    👤 Alumno: {matricula[MATRICULA_USUARIO_NOMBRE]} {matricula[MATRICULA_USUARIO_APELLIDOS]}\n"
                    texto += f"        • {reaccion[REACCION_EMOJI]} - {reaccion[REACCION_CANTIDAD]}\n"
            else:
                texto = "❌ No tienes reacciones recibidas."

        elif user and user[0][USUARIO_TIPO] == USUARIO_TIPO_ESTUDIANTE:
            user = user[0]
            reacciones = get_reacciones(REACCION_ID_ALUMNO=user[USUARIO_ID])
            reacciones.sort(key=lambda x: (x[REACCION_ID_ASIGNATURA], x[REACCION_ID_PROFESOR]))
            matriculas = get_matriculas_asignatura_de_usuario(MATRICULA_ID_USUARIO=user[USUARIO_ID], MATRICULA_TIPO=MATRICULA_TODAS)
            
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
                        print(matriculas,"\n\n\n", reaccion,"\n\n\n")
                        if reaccion[REACCION_ID_ASIGNATURA] != 1:
                            matricula = next((item for item in matriculas if (item[MATRICULA_ID_ASIGNATURA] == reaccion[REACCION_ID_ASIGNATURA])), None)
                        else:
                            matricula = {
                                MATRICULA_ASIGNATURA_NOMBRE_CORTO:"Tutoria"
                            }
                        if matricula:
                            texto += f"📚 Asignatura: {matricula[MATRICULA_ASIGNATURA_NOMBRE_CORTO]}\n"
                    if last_profesor != reaccion[REACCION_ID_PROFESOR]:
                        if last_profesor is not None:
                            texto += "\n"
                        last_profesor = reaccion[REACCION_ID_PROFESOR]
                        
                        matricula = next((item for item in matriculas if (item[MATRICULA_ID_USUARIO] == reaccion[REACCION_ID_ALUMNO])), None)
                        if matricula:
                            texto += f"    👤 Profesor: {matricula[MATRICULA_USUARIO_NOMBRE]} {matricula[MATRICULA_USUARIO_APELLIDOS]}\n"
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
        profesor = get_usuarios_local(USUARIO_ID_TELEGRAM=user_id)
        texto = None
        markup = None

        # Verificar que el usuario es profesor
        if profesor and profesor[0][USUARIO_TIPO] == USUARIO_TIPO_PROFESOR:
            profesor = profesor[0]
            texto = f"📩 Selecciona la asignatura de la que quieras el historial de mensajes:\n\n"
            matriculas = get_matriculas_asignatura_de_usuario(MATRICULA_ID_USUARIO=profesor[USUARIO_ID])
            markup = types.InlineKeyboardMarkup()

            callback_data = f"{MENSAJES}1"
            markup.add(types.InlineKeyboardButton(text="Tutorias", callback_data=callback_data))

            if matriculas:
                for asig in matriculas:
                    callback_data = f"{MENSAJES}{asig[MATRICULA_ID_ASIGNATURA]}"
                    markup.add(types.InlineKeyboardButton(text=asig[MATRICULA_ASIGNATURA_NOMBRE], callback_data=callback_data))
            
            
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
    def handle_mensajes(call):
        user_id = call.from_user.id
        id_asignatura = call.data.split('_')[1]  # Extraer ID de la asignatura

        profesor = get_usuarios_local(USUARIO_ID_TELEGRAM=user_id)

        if not profesor or profesor[0][USUARIO_TIPO] != USUARIO_TIPO_PROFESOR:
            bot.answer_callback_query(call.id, "❌ Solo profesores pueden ver mensajes.")
            return
        
        profesor = profesor[0]

        mensajes = get_mensajes(MENSAJE_ID_ASIGNATURA=id_asignatura, MENSAJE_ID_PROFESOR=profesor[USUARIO_ID])
        matriculas = []
        asignatura = ""
        if id_asignatura != "1":
            matriculas = get_matriculas_asignatura_de_usuario(MATRICULA_ID_ASIGNATURA=id_asignatura, MATRICULA_TIPO=MATRICULA_TODAS)
            asignatura = get_asignaturas(ASIGNATURA_ID=id_asignatura)[0][ASIGNATURA_NOMBRE_CORTO]
        else:
            matriculas = get_matriculas_asignatura_de_usuario(MATRICULA_ID_USUARIO=profesor[USUARIO_ID], MATRICULA_TIPO=MATRICULA_TODAS)
            asignatura = "Tutorias"
        mensajes_dict = defaultdict(dict)

        if not asignatura:
            bot.answer_callback_query(call.id, "❌ Asignatura seleccionada invalida.")
            return

        if not mensajes:
            bot.answer_callback_query(call.id, "❌ No hay mensajes para esta asignatura.")
            return

        mensajes.sort(key=lambda x: x[MENSAJE_FECHA])
        texto = f"📩 Historial de mensajes para la asignatura:\n\n"
        for mensaje in mensajes:
            if mensaje[MENSAJE_ID_CHAT] not in mensajes_dict:
                mensajes_dict[mensaje[MENSAJE_ID_CHAT]] = defaultdict(dict)

            mensajes_dict[mensaje[MENSAJE_ID_CHAT]][f"M_{mensaje[MENSAJE_ID_TELEGRAM]}"] = {
                "ID Mensaje": mensaje[MENSAJE_ID_TELEGRAM],
                "Fecha": mensaje[MENSAJE_FECHA],
                "Nombre": "No registrado",
                "Texto": mensaje[MENSAJE_TEXTO],
            }
            matricula = next(item for item in matriculas 
                            if (int(item[MATRICULA_ID_USUARIO]) == mensaje[MENSAJE_ID_SENDER] 
                            and int(item[MATRICULA_ID_ASIGNATURA]) == mensaje[MENSAJE_ID_ASIGNATURA]))
            if matricula:
                mensajes_dict[mensaje[MENSAJE_ID_CHAT]][f"M_{mensaje[MENSAJE_ID_TELEGRAM]}"]["Nombre"] = f"{matricula[MATRICULA_USUARIO_NOMBRE]} {matricula[MATRICULA_USUARIO_APELLIDOS]}"
        try:
            
            data_sorter = dict2xml.DataSorter.never()
            xml = dict2xml.dict2xml(mensajes_dict, wrap=asignatura, data_sorter=data_sorter)

            matricula = next(item for item in matriculas if item[MATRICULA_ID_USUARIO] == profesor[USUARIO_ID])

            ruta_xml = f"./tmp/mensajes_{asignatura}_{matricula[MATRICULA_USUARIO_NOMBRE]}_{matricula[MATRICULA_USUARIO_APELLIDOS]}.xml"
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
