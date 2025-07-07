from db.constantes import USUARIO_TIPO, USUARIO_TIPO_PROFESOR
from db.queries import get_grupos_tutoria, get_usuarios

from telebot import types
import time

from handlers_grupo.utils import configurar_logger

logger = configurar_logger()

def register_handlers(bot):

    @bot.message_handler(func=lambda message: message.text == "❌ Terminar Tutoria")
    def handle_terminar_tutoria(message):
        """Maneja la acción de terminar tutoría según el rol del usuario"""
        chat_id = message.chat.id
        user_id = message.from_user.id

        print(f"\n==================================================")
        print(f"⚠️⚠️⚠️ BOTÓN TERMINAR TUTORÍA PRESIONADO ⚠️⚠️⚠️")
        print(f"⚠️ Chat ID: {chat_id} | User ID: {user_id}")
        print(f"⚠️ Usuario: {message.from_user.first_name}")
        print("==================================================\n")

        try:
            # Verificar que estamos en una grupo de tutoría
            grupo = get_grupos_tutoria(GRUPO_ID_CHAT=str(chat_id))

            if not grupo:
                bot.send_message(chat_id, "Esta función solo está disponible en grupos de tutoría.")
                return

            grupo = grupo[0]

            # Verificar el rol del usuario
            user = get_usuarios(USUARIO_ID_TELEGRAM=user_id)

            if not user:
                bot.send_message(chat_id, "No estás registrado en el sistema.")
                return

            user = user[0]


            # Comportamiento diferente según el rol
            if user[USUARIO_TIPO] == USUARIO_TIPO_PROFESOR:
                # Es profesor: mostrar lista de alumnos para expulsar
                print(f"👨‍🏫 {user_id} ES PROFESOR - Mostrando lista de estudiantes")

                # Crear lista de estudiantes para seleccionar
                markup = types.InlineKeyboardMarkup(row_width=1)

                # Obtener miembros del grupo que no son administradores
                try:
                    chat_admins = bot.get_chat_administrators(chat_id)
                    admin_ids = [admin.user.id for admin in chat_admins]

                    # Obtener todos los miembros
                    chat_members = []
                    offset = 0
                    limit = 50  # Límite por consulta

                    while True:
                        members_chunk = bot.get_chat_members(chat_id, offset=offset, limit=limit)
                        if not members_chunk:
                            break
                        chat_members.extend(members_chunk)
                        offset += limit
                        if len(members_chunk) < limit:
                            break

                    # Filtrar estudiantes (no administradores)
                    estudiantes = [m for m in chat_members if m.user.id not in admin_ids]

                    if not estudiantes:
                        bot.send_message(chat_id, "No hay estudiantes en este grupo para finalizar sesión.")
                        return

                    # Crear botones para cada estudiante
                    for estudiante in estudiantes:
                        nombre = estudiante.user.first_name
                        if estudiante.user.last_name:
                            nombre += f" {estudiante.user.last_name}"
                        markup.add(
                            types.InlineKeyboardButton(
                                nombre,
                                callback_data=f"terminar_{estudiante.user.id}"
                            )
                        )

                    # Añadir botón de cancelar
                    markup.add(types.InlineKeyboardButton("Cancelar", callback_data="cancelar_terminar"))

                    # Enviar mensaje con la lista
                    bot.send_message(
                        chat_id,
                        "Selecciona el estudiante cuya sesión deseas finalizar:",
                        reply_markup=markup
                    )

                except Exception as e:
                    print(f"❌ Error al obtener miembros del grupo: {e}")
                    bot.send_message(
                        chat_id,
                        "No pude obtener la lista de estudiantes. Asegúrate de que tengo permisos de administrador."
                    )

            else:
                # Es estudiante: auto-expulsión
                print(f"🎓 {user_id} ES ESTUDIANTE - Ejecutando auto-expulsión")

                try:
                    # Obtener el nombre del estudiante
                    nombre = message.from_user.first_name
                    if message.from_user.last_name:
                        nombre += f" {message.from_user.last_name}"

                    # Informar en el grupo antes de expulsar
                    bot.send_message(
                        chat_id,
                        f"👋 {nombre} ha finalizado su sesión de tutoría."
                    )

                    # Expulsar al usuario (ban temporal de 30 segundos)
                    until_date = int(time.time()) + 30
                    bot.ban_chat_member(chat_id, user_id, until_date=until_date)

                    # Enviar mensaje privado al estudiante
                    try:
                        bot.send_message(
                            user_id,
                            "Has finalizado tu sesión de tutoría. ¡Gracias por participar!"
                        )
                    except Exception as dm_error:
                        print(f"No se pudo enviar mensaje privado al usuario: {dm_error}")

                except Exception as e:
                    print(f"❌ Error en auto-expulsión: {e}")
                    bot.send_message(
                        chat_id,
                        "No pude procesar tu solicitud. Asegúrate de que el bot sea administrador con permisos suficientes."
                    )

        except Exception as e:
            print(f"❌❌❌ ERROR EN HANDLER TERMINAR TUTORÍA: {e}")
            bot.send_message(chat_id, "Ocurrió un error al procesar tu solicitud.")


    @bot.callback_query_handler(func=lambda call: call.data.startswith("terminar_") or call.data == "cancelar_terminar")
    def handle_terminar_estudiante(call):
        """Procesa la selección del profesor para terminar la sesión de un estudiante"""
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        user_id = call.from_user.id

        print(f"\n==================================================")
        print(f"⚠️⚠️⚠️ CALLBACK TERMINAR ESTUDIANTE ⚠️⚠️⚠️")
        print(f"⚠️ Chat ID: {chat_id} | User ID: {user_id}")
        print(f"⚠️ Callback data: {call.data}")
        print("==================================================\n")

        try:
            # Verificar que es profesor
            user = get_usuarios(USUARIO_ID_TELEGRAM=user_id)
            if not user or user[0][USUARIO_TIPO] != USUARIO_TIPO_PROFESOR:
                bot.answer_callback_query(call.id, "Solo los profesores pueden usar esta función.")
                return
            user = user[0]

            # Cancelar operación si se solicita
            if call.data == "cancelar_terminar":
                bot.edit_message_text(
                    "Operación cancelada.",
                    chat_id=chat_id,
                    message_id=message_id
                )
                bot.answer_callback_query(call.id)
                return

            # Obtener ID del estudiante a expulsar
            estudiante_id = int(call.data.split("_")[1])

            try:
                # Obtener información del estudiante
                estudiante_info = bot.get_chat_member(chat_id, estudiante_id)
                nombre = estudiante_info.user.first_name
                if estudiante_info.user.last_name:
                    nombre += f" {estudiante_info.user.last_name}"

                # Informar al grupo
                bot.send_message(
                    chat_id,
                    f"👋 El profesor ha finalizado la sesión de tutoría con {nombre}."
                )

                # Expulsar al estudiante (ban temporal de 30 segundos)
                until_date = int(time.time()) + 30
                bot.ban_chat_member(chat_id, estudiante_id, until_date=until_date)

                # Enviar mensaje privado al estudiante
                try:
                    bot.send_message(
                        estudiante_id,
                        "El profesor ha finalizado tu sesión de tutoría. ¡Gracias por participar!"
                    )
                except Exception as dm_error:
                    print(f"No se pudo enviar mensaje privado al estudiante: {dm_error}")

                # Confirmar al profesor
                bot.edit_message_text(
                    f"✅ Has finalizado la sesión de tutoría con {nombre}.",
                    chat_id=chat_id,
                    message_id=message_id
                )

            except Exception as e:
                print(f"❌ Error al expulsar estudiante: {e}")
                bot.edit_message_text(
                    "No pude finalizar la sesión del estudiante. Asegúrate de que tengo permisos de administrador.",
                    chat_id=chat_id,
                    message_id=message_id
                )

        except Exception as e:
            print(f"❌❌❌ ERROR EN CALLBACK TERMINAR ESTUDIANTE: {e}")
            bot.answer_callback_query(call.id, "Ocurrió un error al procesar tu solicitud.")