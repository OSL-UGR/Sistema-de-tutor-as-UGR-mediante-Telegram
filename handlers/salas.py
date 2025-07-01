# Handlers para cambio de propósito de salas de tutoría
import logging
import os
import sys
import telebot
from db.queries import delete_grupo_tutoria, delete_todos_miembros_grupo, get_grupos_tutoria, get_miembros_grupos, get_usuarios, get_usuarios_by_multiple_ids, update_grupo_tutoria
from telebot import types

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='logs/salas.log')

import traceback

def escape_markdown(text):
    """Escapa caracteres especiales de Markdown"""
    if not text:
        return ""
    
    chars = ['_', '*', '`', '[', ']', '(', ')', '#', '+', '-', '.', '!']
    for char in chars:
        text = text.replace(char, '\\' + char)
    
    return text

def register_handlers(bot):

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_sala_"))
    def handle_edit_sala(call):
        """Muestra opciones para editar una sala"""
        chat_id = call.message.chat.id
        print(f"\n\n### INICIO EDIT_SALA - Callback: {call.data} ###")

        try:
            sala_id = int(call.data.split("_")[2])
            print(f"🔍 Sala ID a editar: {sala_id}")

            # Verificar que el usuario es el propietario de la sala
            user = get_usuarios(TelegramID=call.from_user.id)[0]
            print(f"👤 Usuario: {user['Nombre'] if user else 'No encontrado'}")

            if not user or user['Tipo'] != 'profesor':
                print("⚠️ Usuario no es profesor o no existe")
                bot.answer_callback_query(call.id, "⚠️ Solo los profesores propietarios pueden editar salas")
                return

            # Obtener datos actuales de la sala
            print(f"🔍 Consultando detalles de sala ID {sala_id}")
            sala = get_grupos_tutoria(id_sala=sala_id, Id_usuario=user['Id_usuario'])[0]

            if not sala:
                print(f"❌ Sala no encontrada o no pertenece al usuario")
                bot.answer_callback_query(call.id, "❌ No se encontró la sala o no tienes permisos")
                return

            print(f"✅ Sala encontrada: {sala['Nombre_sala']} (Chat ID: {sala['Chat_id']})")

            # Mostrar opciones simplificadas (solo eliminar)
            print("🔘 Generando botón de eliminación...")
            markup = types.InlineKeyboardMarkup(row_width=1)

            # Añadir opción para eliminar la sala
            markup.add(types.InlineKeyboardButton(
                "🗑️ Eliminar sala",
                callback_data=f"eliminarsala_{sala_id}"
            ))
            print(f"  ✓ Botón eliminar con callback: eliminarsala_{sala_id}")

            # Botón para cancelar
            markup.add(types.InlineKeyboardButton(
                "❌ Cancelar",
                callback_data=f"cancelar_edicion_{sala_id}"
            ))

            # Preparar textos seguros para Markdown
            nombre_sala = escape_markdown(sala['Nombre_sala'])
            nombre_asignatura = escape_markdown(sala['Asignatura'] or 'General')

            print(f"📤 Enviando mensaje de edición")
            bot.edit_message_text(
                f"🔄 *Gestionar sala*\n\n"
                f"*Sala:* {nombre_sala}\n"
                f"*Asignatura:* {nombre_asignatura}\n\n"
                f"Selecciona la acción que deseas realizar:",
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
            print("✅ Mensaje de opciones enviado")

        except Exception as e:
            print(f"❌ ERROR en handle_edit_sala: {e}")
            import traceback
            print(traceback.format_exc())

        bot.answer_callback_query(call.id)
        print("✅ Respuesta de callback enviada")
        print(f"### FIN EDIT_SALA - Callback: {call.data} ###\n")


    def realizar_cambio_proposito(chat_id, message_id, sala_id, nuevo_proposito, user_id):
        """Realiza el cambio de propósito cuando no hay miembros que gestionar"""
        try:
            # Obtener datos actuales de la sala
            sala = get_grupos_tutoria(id_sala=sala_id)[0]

            if not sala:
                bot.edit_message_text(
                    "❌ Error: No se encontró la sala",
                    chat_id=chat_id,
                    message_id=message_id
                )
                return

            # Actualizar tipo
            tipo_sala = 'pública' if nuevo_proposito == 'avisos' else 'privada'

            # Actualizar propósito
            update_grupo_tutoria(
                sala_id,
                Proposito_sala=nuevo_proposito,
                Id_usuario=user_id,
                Tipo_sala=tipo_sala,
                do_commit=True
            )

            # Generar nuevo nombre según el propósito
            nuevo_nombre = None
            if nuevo_proposito == 'avisos':
                nuevo_nombre = f"Avisos: {sala['Asignatura']}"
            elif nuevo_proposito == 'individual':
                nombre_prof = get_usuarios(Id_usuario=user_id)[0]
                nuevo_nombre = f"Tutoría Privada - Prof. {nombre_prof['Nombre'] if nombre_prof else "Profesor"}"

            # Si se generó un nuevo nombre, actualizar en la base de datos
            if nuevo_nombre:
                update_grupo_tutoria(
                    sala_id,
                    Nombre_sala=nuevo_nombre,
                    do_commit=True
                )

                # Intentar cambiar el nombre del grupo en Telegram
                telegram_chat_id = sala['Chat_id']

                # Primero intentar con el bot actual (aunque probablemente fallará)
                try:
                    bot.set_chat_title(telegram_chat_id, nuevo_nombre)
                    print(f"✅ Nombre del grupo actualizado a: {nuevo_nombre}")
                except Exception as e:
                    print(f"⚠️ Bot principal no pudo cambiar el nombre: {e}")

                    # Si falla, utilizar la función del bot de grupos
                    try:
                        # Importar la función de cambio de nombre de grupos.py
                        from handlers_grupo.grupos import cambiar_nombre_grupo_telegram

                        # Llamar a la función para cambiar el nombre
                        if cambiar_nombre_grupo_telegram(telegram_chat_id, nuevo_nombre):
                            print(f"✅ Nombre del grupo actualizado usando el bot de grupos")
                        else:
                            print(f"❌ No se pudo cambiar el nombre del grupo ni siquiera con el bot de grupos")
                    except Exception as e:
                        print(f"❌ Error al intentar utilizar la función del bot de grupos: {e}")

            # Obtener info actualizada
            sala_actualizada = get_grupos_tutoria(id_sala=sala_id)[0]

            # Textos para los propósitos
            propositos = {
                'individual': 'Tutorías individuales',
                'grupal': 'Tutorías grupales',
                'avisos': 'Canal de avisos'
            }

            # Enviar confirmación
            bot.edit_message_text(
                f"✅ *¡Propósito actualizado correctamente!*\n\n"
                f"*Sala:* {sala_actualizada['Nombre_sala']}\n"
                f"*Nuevo propósito:* {propositos.get(nuevo_proposito, 'General')}\n"
                f"*Asignatura:* {sala_actualizada['Asignatura'] or 'General'}\n\n"
                f"La sala está lista para su nuevo propósito.",
                chat_id=chat_id,
                message_id=message_id,
                parse_mode="Markdown"
            )

        except Exception as e:
            print(f"Error al actualizar sala: {e}")
            bot.send_message(chat_id, "❌ Error al actualizar la sala")


    @bot.callback_query_handler(func=lambda call: call.data.startswith("cambiar_proposito_"))
    def handle_cambiar_proposito(call):
        """Muestra opciones para gestionar miembros al cambiar el propósito de la sala"""
        chat_id = call.message.chat.id
        data = call.data.split("_")
        sala_id = int(data[2])
        nuevo_proposito = data[3]

        # Verificar usuario
        user = get_usuarios(TelegramID=call.from_user.id)[0]
        if not user or user['Tipo'] != 'profesor':
            bot.answer_callback_query(call.id, "⚠️ No tienes permisos para esta acción")
            return

        # Obtener datos de la sala
        sala = get_grupos_tutoria(id_sala=sala_id, Id_usuario=user['Id_usuario'])[0]

        # Contar miembros actuales
        miembros = len(get_miembros_grupos(id_sala=sala_id, Estado='activo'))

        total_miembros = miembros if miembros else 0

        # Si no hay miembros, cambiar directamente
        if total_miembros == 0:
            realizar_cambio_proposito(chat_id, call.message.message_id, sala_id, nuevo_proposito, user['Id_usuario'])
            bot.answer_callback_query(call.id)
            return

        # Textos descriptivos según el tipo de cambio
        propositos = {
            'individual': 'Tutorías individuales (requiere aprobación)',
            'grupal': 'Tutorías grupales',
            'avisos': 'Canal de avisos (acceso público)'
        }

        # Escapar todos los textos dinámicos
        nombre_sala = escape_markdown(sala['Nombre_sala'])
        nombre_asignatura = escape_markdown(sala['Asignatura'] or 'General')
        prop_actual = escape_markdown(propositos.get(sala['Proposito_sala'], 'General'))
        prop_nueva = escape_markdown(propositos.get(nuevo_proposito, 'General'))

        # Determinar qué tipo de cambio es
        cambio_tipo = f"{sala['Proposito_sala']}_{nuevo_proposito}"
        titulo_decision = ""

        if cambio_tipo == "avisos_individual":
            titulo_decision = (
                f"🔄 Estás cambiando de *canal de avisos* a *tutorías individuales*.\n"
                f"Esto hará que los nuevos accesos requieran tu aprobación."
            )
        elif cambio_tipo == "individual_avisos":
            titulo_decision = (
                f"🔄 Estás cambiando de *tutorías individuales* a *canal de avisos*.\n"
                f"Esto permitirá que cualquier estudiante matriculado acceda directamente."
            )
        else:
            titulo_decision = f"🔄 Estás cambiando el propósito de la sala de *{prop_actual}* a *{prop_nueva}*."

        # Mostrar opciones para gestionar miembros
        markup = types.InlineKeyboardMarkup(row_width=1)

        markup.add(types.InlineKeyboardButton(
            f"✅ Mantener a los {total_miembros} miembros actuales",
            callback_data=f"confirmar_cambio_{sala_id}_{nuevo_proposito}_mantener"
        ))

        markup.add(types.InlineKeyboardButton(
            "❌ Eliminar a todos los miembros actuales",
            callback_data=f"confirmar_cambio_{sala_id}_{nuevo_proposito}_eliminar"
        ))

        markup.add(types.InlineKeyboardButton(
            "🔍 Ver lista de miembros antes de decidir",
            callback_data=f"ver_miembros_{sala_id}_{nuevo_proposito}"
        ))

        markup.add(types.InlineKeyboardButton(
            "↩️ Cancelar cambio",
            callback_data=f"cancelar_edicion_{sala_id}"
        ))

        # Enviar mensaje con opciones
        bot.edit_message_text(
            f"{titulo_decision}\n\n"
            f"*Sala:* {nombre_sala}\n"
            f"*Miembros actuales:* {total_miembros}\n"
            f"*Asignatura:* {nombre_asignatura}\n\n"
            f"¿Qué deseas hacer con los miembros actuales?",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )

        bot.answer_callback_query(call.id)


    def notificar_cambio_sala(sala_id, nuevo_proposito):
        """Notifica a los miembros de la sala sobre el cambio de propósito"""
        # Obtener datos de la sala
        sala = get_grupos_tutoria(id_sala=sala_id)[0]

        if not sala:
            return

        # Obtener miembros de la sala
        miembros = get_miembros_grupos(id_sala=sala_id, Estado='activo')
        ids_miembros = [m['Id_usuario'] for m in miembros]
        miembros_datos = get_usuarios_by_multiple_ids(ids_miembros)

        miembros_datos.sort(key=lambda x: (x['Nombre']+" "+x['Apellidos']))
        orden = {d['Id_usuario']: i for i, d in enumerate(miembros_datos)}
        miembros.sort(key=lambda x: orden[x["Id_usuario"]])

        # Textos para los propósitos (simplificado)
        propositos = {
            'individual': 'Tutorías individuales',
            'avisos': 'Canal de avisos'
        }

        # Textos explicativos según el nuevo propósito
        explicaciones = {
            'individual': (
                "Ahora la sala requiere aprobación del profesor para cada solicitud "
                "y solo está disponible durante su horario de tutorías."
            ),
            'avisos': (
                "Ahora la sala funciona como canal informativo donde "
                "el profesor comparte anuncios importantes para todos los estudiantes."
            )
        }

        # Notificar a cada miembro
        for miembro in miembros_datos:
            if miembro['TelegramID']:
                try:
                    bot.send_message(
                        miembro['TelegramID'],
                        f"ℹ️ *Cambio en sala de tutoría*\n\n"
                        f"El profesor *{sala['Profesor']}* ha modificado el propósito "
                        f"de la sala *{sala['Nombre_sala']}*.\n\n"
                        f"*Nuevo propósito:* {propositos.get(nuevo_proposito, 'General')}\n"
                        f"*Asignatura:* {sala['Asignatura'] or 'General'}\n\n"
                        f"{explicaciones.get(nuevo_proposito, '')}\n\n"
                        f"Tu acceso a la sala se mantiene, pero la forma de interactuar "
                        f"podría cambiar según el nuevo propósito.",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    print(f"Error al notificar a usuario {miembro['Id_usuario']}: {e}")


    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirmar_cambio_"))
    def handle_confirmar_cambio(call):
        """Confirma el cambio de propósito con la decisión sobre los miembros"""
        chat_id = call.message.chat.id
        data = call.data.split("_")
        sala_id = int(data[2])
        nuevo_proposito = data[3]
        decision_miembros = data[4]  # "mantener" o "eliminar"

        # Verificar usuario
        user = get_usuarios(TelegramID=call.from_user.id)[0]
        if not user or user['Tipo'] != 'profesor':
            bot.answer_callback_query(call.id, "⚠️ No tienes permisos para esta acción")
            return

        # Realizar el cambio de propósito    
        try:
            # Obtener información de la sala
            sala = get_grupos_tutoria(id_sala=sala_id)[0]

            if not sala:
                bot.answer_callback_query(call.id, "❌ Error: No se encontró la sala")
                return

            # Determinar el tipo de sala según el nuevo propósito
            tipo_sala = 'pública' if nuevo_proposito == 'avisos' else 'privada'

            update_grupo_tutoria(
                sala_id,
                Tipo_sala=tipo_sala,
                Proposito_sala=nuevo_proposito,
                Id_usuario=user['Id_usuario'],
                do_commit=True
            )

            # Generar nombre según el propósito
            nuevo_nombre = None
            if nuevo_proposito == 'avisos':
                nuevo_nombre = f"Avisos: {sala['Asignatura']}"
            elif nuevo_proposito == 'individual':
                nuevo_nombre = f"Tutoría Privada - Prof. {sala['Profesor']}"

            # Actualizar el nombre en la BD
            if nuevo_nombre:
                update_grupo_tutoria(
                    sala_id,
                    Nombre_sala=nuevo_nombre,
                    do_commit=True
                )

                # Intentar cambiar el nombre en Telegram
                telegram_chat_id = sala['Chat_id']

                # Primero intentar con el bot actual (aunque probablemente fallará)
                try:
                    bot.set_chat_title(telegram_chat_id, nuevo_nombre)
                    print(f"✅ Nombre del grupo actualizado a: {nuevo_nombre}")
                except Exception as e:
                    print(f"⚠️ Bot principal no pudo cambiar el nombre: {e}")

                    # Si falla, utilizar la función del bot de grupos
                    try:
                        # Importar la función de cambio de nombre de grupos.py
                        from handlers_grupo.grupos import cambiar_nombre_grupo_telegram

                        # Llamar a la función para cambiar el nombre
                        if cambiar_nombre_grupo_telegram(telegram_chat_id, nuevo_nombre):
                            print(f"✅ Nombre del grupo actualizado usando el bot de grupos")
                        else:
                            print(f"❌ No se pudo cambiar el nombre del grupo ni siquiera con el bot de grupos")
                    except Exception as e:
                        print(f"❌ Error al intentar utilizar la función del bot de grupos: {e}")

            # 4. Gestionar miembros según la decisión
            if decision_miembros == "eliminar":
                # Eliminar todos los miembros excepto el profesor creador
                delete_todos_miembros_grupo(sala_id)

            # Obtener información actualizada de la sala
            sala = get_grupos_tutoria(id_sala=sala_id)[0]

            # Contar miembros restantes
            miembros = len(get_miembros_grupos(id_sala=sala_id, Estado='activo'))
            total_miembros = miembros if miembros else 0

            # Textos para los propósitos
            propositos = {
                'individual': 'Tutorías individuales',
                'grupal': 'Tutorías grupales',
                'avisos': 'Canal de avisos'
            }

            # Escapar textos que pueden contener caracteres Markdown
            nombre_sala = escape_markdown(sala['Nombre_sala'])
            nombre_asignatura = escape_markdown(sala['Asignatura'] or 'General')
            prop_nueva = escape_markdown(propositos.get(nuevo_proposito, 'General'))

            # Mensaje de éxito
            mensaje_exito = (
                f"✅ *¡Propósito actualizado correctamente!*\n\n"
                f"*Sala:* {nombre_sala}\n"
                f"*Nuevo propósito:* {prop_nueva}\n"
                f"*Asignatura:* {nombre_asignatura}\n"
                f"*Miembros actuales:* {total_miembros}\n\n"
            )

            # Agregar mensaje según la decisión tomada
            if decision_miembros == "eliminar":
                mensaje_exito += (
                    "🧹 Se han eliminado todos los miembros anteriores.\n"
                    "La sala está lista para su nuevo propósito."
                )
            else:
                mensaje_exito += (
                    "👥 Se han mantenido todos los miembros anteriores.\n"
                    "Se ha notificado a los miembros del cambio de propósito."
                )
                # Notificar a los miembros del cambio
                notificar_cambio_sala(sala_id, nuevo_proposito)

            # Editar mensaje con confirmación
            try:
                bot.edit_message_text(
                    mensaje_exito,
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    parse_mode="Markdown"
                )
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e):
                    pass  # Ignorar este error específico
                else:
                    # Manejar otros errores
                    print(f"Error al editar mensaje de confirmación: {e}")
                    bot.send_message(chat_id, mensaje_exito, parse_mode="Markdown")

        except Exception as e:
            print(f"Error al actualizar sala: {e}")
            bot.answer_callback_query(call.id, "❌ Error al actualizar la sala")


        bot.answer_callback_query(call.id)


    @bot.callback_query_handler(func=lambda call: call.data.startswith("ver_miembros_"))
    def handle_ver_miembros(call):
        """Muestra la lista de miembros de la sala antes de decidir"""
        chat_id = call.message.chat.id
        data = call.data.split("_")
        sala_id = int(data[2])
        nuevo_proposito = data[3]

        # Verificar usuario
        user = get_usuarios(TelegramID=call.from_user.id)[0]
        if not user or user['Tipo'] != 'profesor':
            bot.answer_callback_query(call.id, "⚠️ No tienes permisos para esta acción")
            return

        # Obtener lista de miembros    
        miembros = get_miembros_grupos(id_sala=sala_id, Estado='activo')
        ids_miembros = [m['Id_usuario'] for m in miembros]
        datos_miembros = get_usuarios_by_multiple_ids(ids_miembros)

        datos_miembros.sort(key=lambda x: (x['Nombre']+" "+x['Apellidos']))
        orden = {d['Id_usuario']: i for i, d in enumerate(datos_miembros)}
        miembros.sort(key=lambda x: orden[x["Id_usuario"]])

        # Obtener información de la sala
        sala = get_grupos_tutoria(id_sala=sala_id)[0]["Nombre_sala"]

        if not miembros:
            # No hay miembros, cambiar directamente
            bot.answer_callback_query(call.id, "No hay miembros en esta sala")
            realizar_cambio_proposito(chat_id, call.message.message_id, sala_id, nuevo_proposito, user['Id_usuario'])
            return

        # Crear mensaje con lista de miembros
        mensaje = f"👥 *Miembros de la sala \"{sala['Nombre_sala']}\":*\n\n"

        for i, (m,d) in enumerate(zip(miembros, datos_miembros), 1):
            nombre_completo = f"{d['Nombre']} {d['Apellidos'] or ''}"
            fecha = m['Fecha_union'].split(' ')[0] if m['Fecha_union'] else 'Desconocida'
            mensaje += f"{i}. *{nombre_completo}*\n   📧 {d['Email_UGR']}\n   📅 Unido: {fecha}\n\n"

        # Botones para continuar
        markup = types.InlineKeyboardMarkup(row_width=1)

        markup.add(types.InlineKeyboardButton(
            f"✅ Mantener a los {len(miembros)} miembros",
            callback_data=f"confirmar_cambio_{sala_id}_{nuevo_proposito}_mantener"
        ))

        markup.add(types.InlineKeyboardButton(
            "❌ Eliminar a todos los miembros",
            callback_data=f"confirmar_cambio_{sala_id}_{nuevo_proposito}_eliminar"
        ))

        markup.add(types.InlineKeyboardButton(
            "↩️ Cancelar cambio",
            callback_data=f"cancelar_edicion_{sala_id}"
        ))

        # Enviar mensaje con lista y opciones
        bot.edit_message_text(
            mensaje,
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode="Markdown"
        )

        bot.answer_callback_query(call.id)


    @bot.callback_query_handler(func=lambda call: call.data.startswith("cancelar_edicion_"))
    def handle_cancelar_edicion(call):
        """Cancela la edición de la sala"""
        bot.edit_message_text(
            "❌ Operación cancelada. No se realizaron cambios.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        bot.answer_callback_query(call.id)


    @bot.callback_query_handler(func=lambda call: call.data.startswith("eliminarsala_"))
    def handle_eliminar_sala(call):
        """Maneja la solicitud de eliminación de una sala"""
        chat_id = call.message.chat.id
        print(f"\n\n### INICIO ELIMINAR_SALA - Callback: {call.data} ###")

        try:
            sala_id = int(call.data.split("_")[1])
            print(f"🔍 Sala ID a eliminar: {sala_id}")

            # Verificar que el usuario es el propietario de la sala
            user = get_usuarios(TelegramID=call.from_user.id)[0]

            if not user or user['Tipo'] != 'profesor':
                print("⚠️ Usuario no es profesor o no existe")
                bot.answer_callback_query(call.id, "⚠️ Solo los profesores propietarios pueden eliminar salas")
                return

            # Obtener datos de la sala
            sala = get_grupos_tutoria(id_sala=sala_id, Id_usuario=user['Id_usuario'])[0]

            if not sala:
                print(f"❌ Sala no encontrada o no pertenece al usuario")
                bot.answer_callback_query(call.id, "❌ No se encontró la sala o no tienes permisos")
                return

            print(f"✅ Sala encontrada: {sala['Nombre_sala']} (Chat ID: {sala['Chat_id']})")

            # Contar miembros actuales
            miembros = len(get_miembros_grupos(id_sala=sala_id, Estado='activo'))
            total_miembros = miembros if miembros else 0

            # Preparar textos seguros para Markdown
            nombre_sala = escape_markdown(sala['Nombre_sala'])
            nombre_asignatura = escape_markdown(sala['Asignatura'] or 'General')

            # Confirmar la eliminación con botones
            markup = types.InlineKeyboardMarkup(row_width=1)

            markup.add(types.InlineKeyboardButton(
                "✅ Sí, eliminar esta sala",
                callback_data=f"confirmar_eliminar_{sala_id}"
            ))

            markup.add(types.InlineKeyboardButton(
                "❌ No, cancelar",
                callback_data=f"cancelar_edicion_{sala_id}"
            ))

            # Enviar mensaje de confirmación
            bot.edit_message_text(
                f"⚠️ *¿Estás seguro de que deseas eliminar esta sala?*\n\n"
                f"*Sala:* {nombre_sala}\n"
                f"*Asignatura:* {nombre_asignatura}\n"
                f"*Miembros actuales:* {total_miembros}\n\n"
                f"Esta acción es irreversible. La sala será eliminada de la base de datos "
                f"y se perderá todo el registro de miembros.",
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )

        except Exception as e:
            print(f"❌ ERROR en handle_eliminar_sala: {e}")
            import traceback
            print(traceback.format_exc())

        bot.answer_callback_query(call.id)
        print("### FIN ELIMINAR_SALA ###")


    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirmar_eliminar_"))
    def handle_confirmar_eliminar(call):
        """Confirma y ejecuta la eliminación de la sala"""
        chat_id = call.message.chat.id
        print(f"\n\n### INICIO CONFIRMAR_ELIMINAR - Callback: {call.data} ###")

        try:
            sala_id = int(call.data.split("_")[2])
            print(f"🔍 Sala ID a eliminar definitivamente: {sala_id}")

            # Verificar que el usuario es el propietario de la sala
            user = get_usuarios(TelegramID=call.from_user.id)[0]

            if not user or user['Tipo'] != 'profesor':
                print("⚠️ Usuario no es profesor o no existe")
                bot.answer_callback_query(call.id, "⚠️ Solo los profesores propietarios pueden eliminar salas")
                return

            # Obtener datos de la sala
            sala = get_grupos_tutoria(id_sala=sala_id, Id_usuario=user['Id_usuario'])[0]

            if not sala:
                print(f"❌ Sala no encontrada o no pertenece al usuario")
                bot.answer_callback_query(call.id, "❌ No se encontró la sala o no tienes permisos")
                return

            nombre_sala = sala['Nombre_sala']
            telegram_chat_id = sala['Chat_id']
            print(f"✅ Ejecutando eliminación de sala: {nombre_sala} (ID: {sala_id}, Chat ID: {telegram_chat_id})")

            # 1. Eliminar todos los miembros de la sala
            print("1️⃣ Eliminando miembros...")
            delete_todos_miembros_grupo(sala_id)
            print(f"  ✓ Miembros eliminados de la BD")

            # 2. Eliminar la sala de la base de datos
            print("2️⃣ Eliminando registro de sala...")
            delete_grupo_tutoria(sala_id)
            print(f"  ✓ Sala eliminada de la BD")

            # Confirmar cambios en la base de datos
            print("✅ Cambios en BD confirmados")

            # 3. Intentar salir del grupo de Telegram
            print("3️⃣ Intentando salir del grupo de Telegram...")
            try:
                bot.leave_chat(telegram_chat_id)
                print(f"  ✓ Bot salió del grupo de Telegram: {telegram_chat_id}")
            except Exception as e:
                print(f"  ⚠️ No se pudo salir del grupo de Telegram: {e}")

                # Intentar con el bot de grupos si está disponible
                try:
                    from handlers_grupo.grupos import salir_de_grupo
                    if salir_de_grupo(telegram_chat_id):
                        print("  ✓ Bot de grupos salió del grupo")
                    else:
                        print("  ⚠️ Bot de grupos no pudo salir del grupo")
                except Exception as e:
                    print(f"  ⚠️ Error al usar la función del bot de grupos: {e}")

            # 4. Enviar mensaje de confirmación
            print("4️⃣ Enviando confirmación al usuario...")
            bot.edit_message_text(
                f"✅ *Sala eliminada con éxito*\n\n"
                f"La sala \"{escape_markdown(nombre_sala)}\" ha sido eliminada completamente.\n"
                f"Todos los miembros y registros asociados han sido eliminados.",
                chat_id=chat_id,
                message_id=call.message.message_id,
                parse_mode="Markdown"
            )
            print("  ✓ Mensaje de confirmación enviado")

        except Exception as e:
            print(f"❌ ERROR en handle_confirmar_eliminar: {e}")
            import traceback
            print(traceback.format_exc())
            bot.edit_message_text(
                "❌ Ha ocurrido un error al intentar eliminar la sala. Por favor, inténtalo de nuevo.",
                chat_id=chat_id,
                message_id=call.message.message_id
            )

        bot.answer_callback_query(call.id)
        print("### FIN CONFIRMAR_ELIMINAR ###")


    @bot.callback_query_handler(func=lambda call: call.data == "ver_salas")
    def handler_ver_salas(call):
        """Muestra las salas actuales del usuario"""
        chat_id = call.message.chat.id
        user_id = call.from_user.id

        # Depuración adicional
        print(f"\n\n### INICIO VER_SALAS CALLBACK ###")
        print(f"🔍 Callback data: {call.data}")
        print(f"👤 User ID: {user_id}, Chat ID: {chat_id}")
        print(f"📝 Message ID: {call.message.message_id}")

        # Responder al callback inmediatamente para evitar el error de "query is too old"
        try:
            bot.answer_callback_query(call.id)
            print("✅ Callback respondido correctamente")
        except Exception as e:
            print(f"❌ Error al responder al callback: {e}")
        
        user_info = ""

        salas = get_grupos_tutoria(Id_usuario=get_usuarios(TelegramID=chat_id)[0]["Id_usuario"])
        print(salas)
        salas.sort(key=lambda x: x["Fecha_creacion"], reverse=True)

        if salas and len(salas) > 0:
            user_info += "\n*🔵 Salas de tutoría creadas:*\n"

            # Diccionario para traducir los propósitos a texto más amigable
            propositos = {
                'individual': 'Tutorías individuales',
                'grupal': 'Tutorías grupales',
                'avisos': 'Canal de avisos'
            }

            for sala in salas:
                # Obtener propósito en formato legible
                proposito = propositos.get(sala['Proposito_sala'], sala['Proposito_sala'] or 'General')

                # Obtener asignatura o indicar que es general
                asignatura = sala['Asignatura'] or 'General'

                # Formato de fecha más amigable
                fecha = sala['Fecha_creacion'].split(' ')[0] if sala['Fecha_creacion'] else 'Desconocida'

                user_info += f"• *{sala['Nombre_sala']}*\n"
                user_info += f"  📋 Propósito: {proposito}\n"
                user_info += f"  📚 Asignatura: {asignatura}\n"
                user_info += f"  📅 Creada: {fecha}\n\n"
        else:
            user_info += "\n*🔵 No has creado salas de tutoría todavía.*\n"
            user_info += "Usa /crear_ grupo _ tutoria para crear una nueva sala.\n"

        # Solución para evitar crear un mensaje simulado
        try:
            bot.send_message(chat_id, user_info, parse_mode="Markdown")

            # Si es profesor y tiene salas, mostrar botones para editar
            if get_usuarios(TelegramID=chat_id)[0]['Tipo'] == 'profesor' and salas and len(salas) > 0:
                markup = types.InlineKeyboardMarkup(row_width=1)
            
                # Añadir SOLO botones para editar cada sala (quitar botones de eliminar)
                for sala in salas:
                    sala_id = sala['id_sala']
                
                    markup.add(types.InlineKeyboardButton(
                        f"✏️ Sala: {sala['Nombre_sala']}",
                        callback_data=f"edit_sala_{sala_id}"
                    ))
            
                bot.send_message(
                    chat_id,
                    "Selecciona una sala para gestionar:",
                    reply_markup=markup
                )
        except Exception as e:
            print(f"❌ Error al llamar a handle_ver_misdatos: {str(e)}")
            import traceback
            print("📋 Traza de error completa:")
            traceback.print_exc()
            bot.send_message(chat_id, "❌ Error al mostrar tus salas. Intenta usar /ver_misdatos directamente.")

        print("### FIN VER_SALAS CALLBACK ###\n\n")


    @bot.message_handler(commands=['crear_grupo_tutoria'])
    def crear_grupo(message):
        """Proporciona instrucciones para crear un grupo de tutoría en Telegram"""
        chat_id = message.chat.id
        user = get_usuarios(TelegramID=message.from_user.id)[0]

        # Verificar que el usuario es profesor
        if not user or user['Tipo'] != 'profesor':
            bot.send_message(
                chat_id,
                "❌ Solo los profesores pueden crear grupos de tutoría."
            )
            return

        # Instrucciones sin formato especial (sin asteriscos ni caracteres problemáticos)
        instrucciones = (
            "🎓 Cómo crear un grupo de tutoría\n\n"
            "Siga estos pasos para crear un grupo de tutoría efectivo:\n\n"

            "1️⃣ Crear un grupo nuevo en Telegram\n"
            "• Pulse el botón de nueva conversación\n"
            "• Seleccione 'Nuevo grupo'\n\n"

            "2️⃣ Añadir el bot al grupo\n"
            "• Pulse el nombre del grupo\n"
            "• Seleccione 'Administradores'\n"
            "• Añada a @UGRBot como administrador\n"
            "• Active todos los permisos\n\n"

            "3️⃣ Configurar el grupo\n"
            "• En el grupo, escriba /configurar_grupo\n"
            "• Siga las instrucciones para vincular la sala\n"
            "• Configure el tipo de tutoría\n\n"

            "📌 Recomendaciones para el nombre del grupo\n"
            "• 'Tutorías [Asignatura] - [Su Nombre]'\n"
            "• 'Avisos [Asignatura] - [Año Académico]'\n\n"

            "🔔 Una vez registrada la sala podrá\n"
            "• Gestionar solicitudes de tutoría\n"
            "• Programar sesiones grupales\n"
            "• Enviar avisos automáticos\n"
            "• Ver estadísticas de participación"
        )

        # Crear botones útiles con callback data simplificados
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(
                "📝 Ver mis salas actuales",
                callback_data="ver_salas"  # Simplificado
            ),
            types.InlineKeyboardButton(
                "❓ Preguntas frecuentes",
                callback_data="faq_grupo"  # Simplificado
            )
        )

        # Enviar mensaje SIN formato markdown para evitar errores
        try:
            bot.send_message(
                chat_id,
                instrucciones,
                reply_markup=markup
            )
        except Exception as e:
            print(f"Error al enviar instrucciones de creación de grupo: {e}")
            bot.send_message(
                chat_id,
                "Para crear un grupo de tutoría: 1) Cree un grupo, 2) Añada al bot como administrador, "
                "3) Use /configurar_grupo en el grupo.",
                reply_markup=markup
            )


    @bot.callback_query_handler(func=lambda call: call.data == "volver_instrucciones")
    def handler_volver_instrucciones(call):
        """Vuelve a mostrar las instrucciones originales"""
        chat_id = call.message.chat.id
        user_id = call.from_user.id

        # Depuración adicional
        print(f"\n\n### INICIO VOLVER_INSTRUCCIONES CALLBACK ###")
        print(f"🔍 Callback data: {call.data}")
        print(f"👤 User ID: {user_id}, Chat ID: {chat_id}")
        print(f"📝 Message ID: {call.message.message_id}")

        # Responder al callback inmediatamente
        try:
            bot.answer_callback_query(call.id)
            print("✅ Callback respondido correctamente")
        except Exception as e:
            print(f"❌ Error al responder al callback: {e}")

        # Solución para evitar crear un mensaje simulado
        try:
            print("🔄 Preparando llamada a crear_grupo...")

            # Crear una clase simple que emule lo necesario de Message
            class SimpleMessage:
                def __init__(self, chat_id, user_id, text):
                    self.chat = types.Chat(chat_id, 'private')
                    self.from_user = types.User(user_id, False, 'Usuario')
                    self.text = text

            # Crear el mensaje simplificado
            msg = SimpleMessage(chat_id, user_id, '/crear_grupo_tutoria')

            # Llamar directamente a la función
            print("🔄 Llamando a crear_grupo...")
            crear_grupo(msg)
            print("✅ crear_grupo llamado con éxito")
        except Exception as e:
            print(f"❌ Error al llamar a crear_grupo: {str(e)}")
            import traceback
            print("📋 Traza de error completa:")
            traceback.print_exc()
            bot.send_message(chat_id, "❌ Error al volver a las instrucciones. Intenta usar /crear_grupo_tutoria directamente.")

        print("### FIN VOLVER_INSTRUCCIONES CALLBACK ###\n\n")

    # Handlers para los botones simplificados
    @bot.callback_query_handler(func=lambda call: call.data == "faq_grupo")
    def handler_faq_grupo(call):
        """Muestra preguntas frecuentes sobre creación de grupos"""
        chat_id = call.message.chat.id
        message_id = call.message.message_id

        # Depuración adicional
        print(f"\n\n### INICIO FAQ_GRUPO CALLBACK ###")
        print(f"🔍 Callback data: {call.data}")
        print(f"👤 User ID: {call.from_user.id}, Chat ID: {chat_id}")
        print(f"📝 Message ID: {message_id}")

        # Responder al callback inmediatamente
        try:
            bot.answer_callback_query(call.id)
            print("✅ Callback respondido correctamente")
        except Exception as e:
            print(f"❌ Error al responder al callback: {e}")

        # FAQ sin formato Markdown para evitar problemas de formato
        faq = (
            "❓ Preguntas frecuentes sobre grupos de tutoría\n\n"

            "¿Puedo crear varios grupos para la misma asignatura?\n"
            "No, solamente un grupo para avisos por asignatura y despues una sala unica para tutorias individuales.\n\n"

            "¿Es necesario hacer administrador al bot?\n"
            "Sí, el bot necesita permisos administrativos para poder gestioanr el grupo.\n\n"

            "¿Quién puede acceder al grupo?\n"
            "Depende del tipo: los de avisos acceden todos los matriculados en la asignatura, los de tutoría individual requieren aprobación por parte del profeser siempre y cuando se encuentre en horario de tutorias.\n\n"

            "¿Puedo cambiar el tipo de grupo después?\n"
            "Sí, use /ver_misdatos y seleccione la sala para modificar su propósito.\n\n"

            "¿Cómo eliminar un grupo?\n"
            "Use /ver_misdatos, seleccione la sala y elija la opción de eliminar.\n\n"

            "¿Los estudiantes pueden crear grupos?\n"
            "No, solo los profesores pueden crear grupos de tutoría oficiales."
        )

        # Botón para volver a las instrucciones
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔙 Volver", callback_data="volver_instrucciones"))
        print("✅ Markup de botones creado")

        try:
            print("🔄 Intentando editar el mensaje actual...")
            # Intentar editar el mensaje actual
            bot.edit_message_text(
                text=faq,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=markup
            )
            print("✅ FAQ enviado con éxito (mensaje editado)")
        except Exception as e:
            print(f"❌ Error al editar mensaje para FAQ: {e}")
            import traceback
            print("📋 Traza de error completa:")
            traceback.print_exc()

            # En caso de error, enviar como mensaje nuevo
            try:
                print("🔄 Intentando enviar como mensaje nuevo...")
                bot.send_message(
                    chat_id,
                    faq,
                    reply_markup=markup
                )
                print("✅ FAQ enviado con éxito (mensaje nuevo)")
            except Exception as e2:
                print(f"❌ Error al enviar mensaje nuevo: {e2}")
                traceback.print_exc()

        print("### FIN FAQ_GRUPO CALLBACK ###\n\n")
