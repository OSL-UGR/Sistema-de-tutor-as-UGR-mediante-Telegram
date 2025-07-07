# Handlers para cambio de propósito de grupos de tutoría
import logging
import os
import sys
import telebot
from db.queries import delete_grupo_tutoria, get_grupos_tutoria, get_usuarios
from db.constantes import *

from telebot import types

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='logs/grupos.log')

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

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_grupo_"))
    def handle_edit_grupo(call):
        """Muestra opciones para editar una grupo"""
        chat_id = call.message.chat.id
        print(f"\n\n### INICIO EDIT_grupo - Callback: {call.data} ###")

        try:
            grupo_id = int(call.data.split("_")[2])
            print(f"🔍 grupo ID a editar: {grupo_id}")

            # Verificar que el usuario es el propietario de la grupo
            user = get_usuarios(USUARIO_ID_TELEGRAM=call.from_user.id)[0]
            print(f"👤 Usuario: {user[USUARIO_NOMBRE] if user else 'No encontrado'}")

            if not user or user[USUARIO_TIPO] != USUARIO_TIPO_PROFESOR:
                print("⚠️ Usuario no es profesor o no existe")
                bot.answer_callback_query(call.id, "⚠️ Solo los profesores propietarios pueden editar grupos")
                return

            # Obtener datos actuales de la grupo
            print(f"🔍 Consultando detalles de grupo ID {grupo_id}")
            grupo = get_grupos_tutoria(GRUPO_ID=grupo_id, GRUPO_ID_USUARIO=user[USUARIO_ID])[0]

            if not grupo:
                print(f"❌ grupo no encontrada o no pertenece al usuario")
                bot.answer_callback_query(call.id, "❌ No se encontró la grupo o no tienes permisos")
                return

            print(f"✅ grupo encontrada: {grupo[GRUPO_NOMBRE]} (Chat ID: {grupo[GRUPO_ID_CHAT]})")

            # Mostrar opciones simplificadas (solo eliminar)
            print("🔘 Generando botón de eliminación...")
            markup = types.InlineKeyboardMarkup(row_width=1)

            # Añadir opción para eliminar la grupo
            markup.add(types.InlineKeyboardButton(
                "🗑️ Eliminar grupo",
                callback_data=f"eliminargrupo_{grupo_id}"
            ))
            print(f"  ✓ Botón eliminar con callback: eliminargrupo_{grupo_id}")

            # Botón para cancelar
            markup.add(types.InlineKeyboardButton(
                "❌ Cancelar",
                callback_data=f"cancelar_edicion_{grupo_id}"
            ))

            # Preparar textos seguros para Markdown
            nombre_grupo = escape_markdown(grupo[GRUPO_NOMBRE])
            nombre_asignatura = escape_markdown(grupo[GRUPO_ASIGNATURA] or 'General')

            print(f"📤 Enviando mensaje de edición")
            bot.edit_message_text(
                f"🔄 *Gestionar grupo*\n\n"
                f"*grupo:* {nombre_grupo}\n"
                f"*Asignatura:* {nombre_asignatura}\n\n"
                f"Selecciona la acción que deseas realizar:",
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )
            print("✅ Mensaje de opciones enviado")

        except Exception as e:
            print(f"❌ ERROR en handle_edit_grupo: {e}")
            import traceback
            print(traceback.format_exc())

        bot.answer_callback_query(call.id)
        print("✅ Respuesta de callback enviada")
        print(f"### FIN EDIT_grupo - Callback: {call.data} ###\n")


    @bot.callback_query_handler(func=lambda call: call.data.startswith("cancelar_edicion_"))
    def handle_cancelar_edicion(call):
        """Cancela la edición de la grupo"""
        bot.edit_message_text(
            "❌ Operación cancelada. No se realizaron cambios.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        bot.answer_callback_query(call.id)


    @bot.callback_query_handler(func=lambda call: call.data.startswith("eliminargrupo_"))
    def handle_eliminar_grupo(call):
        """Maneja la solicitud de eliminación de una grupo"""
        chat_id = call.message.chat.id
        print(f"\n\n### INICIO ELIMINAR_grupo - Callback: {call.data} ###")

        try:
            grupo_id = int(call.data.split("_")[1])
            print(f"🔍 grupo ID a eliminar: {grupo_id}")

            # Verificar que el usuario es el propietario de la grupo
            user = get_usuarios(USUARIO_ID_TELEGRAM=call.from_user.id)[0]

            if not user or user[USUARIO_TIPO] != USUARIO_TIPO_PROFESOR:
                print("⚠️ Usuario no es profesor o no existe")
                bot.answer_callback_query(call.id, "⚠️ Solo los profesores propietarios pueden eliminar grupos")
                return

            # Obtener datos de la grupo
            grupo = get_grupos_tutoria(GRUPO_ID=grupo_id, GRUPO_ID_USUARIO=user[USUARIO_ID])[0]

            if not grupo:
                print(f"❌ grupo no encontrada o no pertenece al usuario")
                bot.answer_callback_query(call.id, "❌ No se encontró la grupo o no tienes permisos")
                return

            print(f"✅ grupo encontrada: {grupo[GRUPO_NOMBRE]} (Chat ID: {grupo[GRUPO_ID_CHAT]})")


            # Preparar textos seguros para Markdown
            nombre_grupo = escape_markdown(grupo[GRUPO_NOMBRE])
            nombre_asignatura = escape_markdown(grupo[GRUPO_ASIGNATURA] or 'General')

            # Confirmar la eliminación con botones
            markup = types.InlineKeyboardMarkup(row_width=1)

            markup.add(types.InlineKeyboardButton(
                "✅ Sí, eliminar esta grupo",
                callback_data=f"confirmar_eliminar_{grupo_id}"
            ))

            markup.add(types.InlineKeyboardButton(
                "❌ No, cancelar",
                callback_data=f"cancelar_edicion_{grupo_id}"
            ))

            # Enviar mensaje de confirmación
            bot.edit_message_text(
                f"⚠️ *¿Estás seguro de que deseas eliminar esta grupo?*\n\n"
                f"*grupo:* {nombre_grupo}\n"
                f"*Asignatura:* {nombre_asignatura}\n"
                f"Esta acción es irreversible. El grupo será eliminado de la base de datos ",
                chat_id=chat_id,
                message_id=call.message.message_id,
                reply_markup=markup,
                parse_mode="Markdown"
            )

        except Exception as e:
            print(f"❌ ERROR en handle_eliminar_grupo: {e}")
            import traceback
            print(traceback.format_exc())

        bot.answer_callback_query(call.id)
        print("### FIN ELIMINAR_grupo ###")


    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirmar_eliminar_"))
    def handle_confirmar_eliminar(call):
        """Confirma y ejecuta la eliminación de la grupo"""
        chat_id = call.message.chat.id
        print(f"\n\n### INICIO CONFIRMAR_ELIMINAR - Callback: {call.data} ###")

        try:
            grupo_id = int(call.data.split("_")[2])
            print(f"🔍 grupo ID a eliminar definitivamente: {grupo_id}")

            # Verificar que el usuario es el propietario de la grupo
            user = get_usuarios(USUARIO_ID_TELEGRAM=call.from_user.id)[0]

            if not user or user[USUARIO_TIPO] != USUARIO_TIPO_PROFESOR:
                print("⚠️ Usuario no es profesor o no existe")
                bot.answer_callback_query(call.id, "⚠️ Solo los profesores propietarios pueden eliminar grupos")
                return

            # Obtener datos de la grupo
            grupo = get_grupos_tutoria(GRUPO_ID=grupo_id, GRUPO_ID_USUARIO=user[USUARIO_ID])[0]

            if not grupo:
                print(f"❌ grupo no encontrada o no pertenece al usuario")
                bot.answer_callback_query(call.id, "❌ No se encontró la grupo o no tienes permisos")
                return

            nombre_grupo = grupo[GRUPO_NOMBRE]
            telegram_chat_id = grupo[GRUPO_ID_CHAT]
            print(f"✅ Ejecutando eliminación de grupo: {nombre_grupo} (ID: {grupo_id}, Chat ID: {telegram_chat_id})")

            # 1. Eliminar la grupo de la base de datos
            print("2️⃣ Eliminando registro de grupo...")
            delete_grupo_tutoria(grupo_id)
            print(f"  ✓ grupo eliminada de la BD")

            # 2. Confirmar cambios en la base de datos
            print("✅ Cambios en BD confirmados")

            # 3. Enviar mensaje de confirmación
            print("4️⃣ Enviando confirmación al usuario...")
            bot.edit_message_text(
                f"✅ *grupo eliminado con éxito*\n\n"
                f"El grupo \"{escape_markdown(nombre_grupo)}\" ha sido eliminado completamente.\n"
                f"Todos los registros asociados han sido eliminados.",
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
                "❌ Ha ocurrido un error al intentar eliminar la grupo. Por favor, inténtalo de nuevo.",
                chat_id=chat_id,
                message_id=call.message.message_id
            )

        bot.answer_callback_query(call.id)
        print("### FIN CONFIRMAR_ELIMINAR ###")


    @bot.callback_query_handler(func=lambda call: call.data == "ver_grupos")
    def handler_ver_grupos(call):
        """Muestra las grupos actuales del usuario"""
        chat_id = call.message.chat.id
        user_id = call.from_user.id

        # Depuración adicional
        print(f"\n\n### INICIO VER_grupoS CALLBACK ###")
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

        grupos = get_grupos_tutoria(GRUPO_ID_USUARIO=get_usuarios(USUARIO_ID_TELEGRAM=chat_id)[0][USUARIO_ID])
        print(grupos)
        grupos.sort(key=lambda x: x[GRUPO_FECHA], reverse=True)

        if grupos and len(grupos) > 0:
            user_info += "\n*🔵 grupos de tutoría creadas:*\n"

            # Diccionario para traducir los propósitos a texto más amigable
            propositos = {
                'individual': 'Tutorías individuales',
                'grupal': 'Tutorías grupales',
                'avisos': 'Canal de avisos'
            }

            for grupo in grupos:
                # Obtener propósito en formato legible
                proposito = propositos.get(grupo[GRUPO_PROPOSITO], grupo[GRUPO_PROPOSITO] or 'General')

                # Obtener asignatura o indicar que es general
                asignatura = grupo[GRUPO_ASIGNATURA] or 'General'

                # Formato de fecha más amigable
                fecha = grupo[GRUPO_FECHA].split(' ')[0] if grupo[GRUPO_FECHA] else 'Desconocida'

                user_info += f"• *{grupo[GRUPO_NOMBRE]}*\n"
                user_info += f"  📋 Propósito: {proposito}\n"
                user_info += f"  📚 Asignatura: {asignatura}\n"
                user_info += f"  📅 Creada: {fecha}\n\n"
        else:
            user_info += "\n*🔵 No has creado grupos de tutoría todavía.*\n"
            user_info += "Usa /crear_ grupo _ tutoria para crear una nueva grupo.\n"

        # Solución para evitar crear un mensaje simulado
        try:
            bot.send_message(chat_id, user_info, parse_mode="Markdown")

            # Si es profesor y tiene grupos, mostrar botones para editar
            if get_usuarios(USUARIO_ID_TELEGRAM=chat_id)[0][USUARIO_TIPO] == USUARIO_TIPO_PROFESOR and grupos and len(grupos) > 0:
                markup = types.InlineKeyboardMarkup(row_width=1)
            
                # Añadir SOLO botones para editar cada grupo (quitar botones de eliminar)
                for grupo in grupos:
                    grupo_id = grupo[GRUPO_ID]
                
                    markup.add(types.InlineKeyboardButton(
                        f"✏️ grupo: {grupo[GRUPO_NOMBRE]}",
                        callback_data=f"edit_grupo_{grupo_id}"
                    ))
            
                bot.send_message(
                    chat_id,
                    "Selecciona una grupo para gestionar:",
                    reply_markup=markup
                )
        except Exception as e:
            print(f"❌ Error al llamar a handle_ver_misdatos: {str(e)}")
            import traceback
            print("📋 Traza de error completa:")
            traceback.print_exc()
            bot.send_message(chat_id, "❌ Error al mostrar tus grupos. Intenta usar /ver_misdatos directamente.")

        print("### FIN VER_grupoS CALLBACK ###\n\n")


    @bot.message_handler(commands=['crear_grupo_tutoria'])
    def crear_grupo(message):
        """Proporciona instrucciones para crear un grupo de tutoría en Telegram"""
        chat_id = message.chat.id
        user = get_usuarios(USUARIO_ID_TELEGRAM=message.from_user.id)[0]

        # Verificar que el usuario es profesor
        if not user or user[USUARIO_TIPO] != USUARIO_TIPO_PROFESOR:
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
            "• Siga las instrucciones para vincular la grupo\n"
            "• Configure el tipo de tutoría\n\n"

            "📌 Recomendaciones para el nombre del grupo\n"
            "• 'Tutorías [Asignatura] - [Su Nombre]'\n"
            "• 'Avisos [Asignatura] - [Año Académico]'\n\n"

            "🔔 Una vez registrada la grupo podrá\n"
            "• Gestionar solicitudes de tutoría\n"
            "• Programar sesiones grupales\n"
            "• Enviar avisos automáticos\n"
            "• Ver estadísticas de participación"
        )

        # Crear botones útiles con callback data simplificados
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(
                "📝 Ver mis grupos actuales",
                callback_data="ver_grupos"  # Simplificado
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
            "No, solamente un grupo para avisos por asignatura y despues una grupo unica para tutorias individuales.\n\n"

            "¿Es necesario hacer administrador al bot?\n"
            "Sí, el bot necesita permisos administrativos para poder gestioanr el grupo.\n\n"

            "¿Quién puede acceder al grupo?\n"
            "Depende del tipo: los de avisos acceden todos los matriculados en la asignatura, los de tutoría individual requieren aprobación por parte del profeser siempre y cuando se encuentre en horario de tutorias.\n\n"

            "¿Puedo cambiar el tipo de grupo después?\n"
            "Sí, use /ver_misdatos y seleccione la grupo para modificar su propósito.\n\n"

            "¿Cómo eliminar un grupo?\n"
            "Use /ver_misdatos, seleccione la grupo y elija la opción de eliminar.\n\n"

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
