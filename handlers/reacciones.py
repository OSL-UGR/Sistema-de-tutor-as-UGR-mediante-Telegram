from telebot import types
import logging
import sys
import os


from handlers.commands import COMMAND_VER_REACCIONES
from db.queries import get_asignaturas, get_usuarios, get_reacciones
from db.constantes import *

# Configuración del logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='logs/horarios.log')


def register_handlers(bot):
    @bot.message_handler(commands=[COMMAND_VER_REACCIONES])
    def handle_ver_reacciones(message, get_text = False):
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
                        last_profesor = None
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