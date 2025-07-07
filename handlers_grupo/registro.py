from db.constantes import ASIGNATURA_ID, ASIGNATURA_NOMBRE, GRUPO_ASIGNATURA, GRUPO_ID, GRUPO_ID_ASIGNATURA, GRUPO_NOMBRE, GRUPO_PRIVADO, GRUPO_PUBLICO, MATRICULA_ASIGNATURA, MATRICULA_ID_ASIGNATURA, MATRICULA_PROFESOR, USUARIO_ID, USUARIO_NOMBRE, USUARIO_TIPO_PROFESOR
from db.queries import get_asignaturas, get_grupos_tutoria, get_matriculas, get_usuarios, insert_grupo_tutoria
from telebot import types
from handlers_grupo.utils import configurar_comandos_por_rol, configurar_logger, es_profesor, menu_estudiante, menu_profesor

import telebot

from utils.state_manager import clear_state, get_state, set_state, user_data

logger = configurar_logger()

def register_handlers(bot):
    def actualizar_interfaz_usuario(user_id, chat_id=None):
        """Actualiza la interfaz completa según el rol del usuario."""
        comandos_profesor, comandos_estudiante = configurar_comandos_por_rol()
        try:
            if es_profesor(user_id):
                # Actualizar comandos visibles
                scope = telebot.types.BotCommandScopeChat(user_id)
                bot.set_my_commands(comandos_profesor, scope)

                # Si hay un chat_id, enviar menú de profesor
                if chat_id:
                    bot.send_message(
                        chat_id,
                        "🔄 Interfaz actualizada para profesor",
                        reply_markup=menu_profesor()
                    )
                logger.info(f"Interfaz de profesor configurada para usuario {user_id}")
            else:
                # Actualizar comandos visibles
                scope = telebot.types.BotCommandScopeChat(user_id)
                bot.set_my_commands(comandos_estudiante, scope)

                # Si hay un chat_id, enviar menú de estudiante
                if chat_id:
                    bot.send_message(
                        chat_id,
                        "🔄 Interfaz actualizada para estudiante",
                        reply_markup=menu_estudiante()
                    )
                logger.info(f"Interfaz de estudiante configurada para usuario {user_id}")
        except Exception as e:
            logger.error(f"Error configurando interfaz para usuario {user_id}: {e}")


    @bot.message_handler(commands=['configurar_grupo'])
    def configurar_grupo(message):
        """
        Inicia el proceso de configuración de un grupo como grupo de tutoría
        """
        chat_id = message.chat.id
        user_id = message.from_user.id

        # Verificar que estamos en un grupo
        if message.chat.type not in ['group', 'supergroup']:
            bot.send_message(chat_id, "⚠️ Este comando solo funciona en grupos.")
            return

        # Verificar que el usuario es profesor
        if not es_profesor(user_id):
            bot.send_message(chat_id, "⚠️ Solo los profesores pueden configurar grupos.")
            return

        # Verificar que el bot tiene permisos de administrador
        bot_member = bot.get_chat_member(chat_id, bot.get_me().id)
        if bot_member.status != 'administrator':
            bot.send_message(
                chat_id,
                "⚠️ Para configurar este grupo necesito ser administrador con permisos para:\n"
                "- Invitar usuarios mediante enlaces\n"
                "- Eliminar mensajes\n"
                "- Restringir usuarios"
            )
            return

        # Verificar si el grupo ya está configurado
        grupo = get_grupos_tutoria(GRUPO_ID_CHAT=str(chat_id))

        if grupo:
            grupo = grupo[0]
            bot.send_message(chat_id, "ℹ️ Este grupo ya está configurado como grupo de tutoría.")
            return

        # Obtener ID del usuario profesor
        profesor_row = get_usuarios(USUARIO_ID_TELEGRAM=str(user_id), USUARIO_TIPO=USUARIO_TIPO_PROFESOR)

        if not profesor_row:
            bot.send_message(chat_id, "⚠️ Solo los profesores registrados pueden configurar grupos.")
            return

        profesor_row = profesor_row[0]

        profesor_id = profesor_row[USUARIO_ID]

        # Obtener SOLO asignaturas sin grupo de avisos asociada

        asignaturas_profesor = get_matriculas(MATRICULA_ID_USUARIO=profesor_id, MATRICULA_TIPO=MATRICULA_PROFESOR)
        grupos = get_grupos_tutoria(GRUPO_ID_USUARIO=profesor_id, GRUPO_TIPO=GRUPO_PUBLICO)
        ids_grupos = [grupo[GRUPO_ID_ASIGNATURA] for grupo in grupos]

        asignaturas_disponibles = []

        for asignatura in asignaturas_profesor:
            if asignatura[ASIGNATURA_ID] not in ids_grupos:
                asignaturas_disponibles.append(asignatura)

        # Verificar si ya tiene grupo de tutoría privada
        tiene_privada = get_grupos_tutoria(GRUPO_ID_USUARIO=profesor_id, GRUPO_TIPO=GRUPO_PRIVADO) != []

        # Depuración - Mostrar grupos actuales
        grupos_actuales = get_grupos_tutoria(GRUPO_ID_USUARIO=profesor_id)
        print(f"\n--- grupoS ACTUALES PARA PROFESOR ID {profesor_id} ---")
        for grupo in grupos_actuales:
            # Usar operador ternario para manejar valores nulos
            nombre_asignatura = grupo[GRUPO_ASIGNATURA] if grupo[GRUPO_ASIGNATURA] is not None else 'N/A'
            print(f"grupo ID: {grupo[GRUPO_ID]}, Nombre: {grupo[GRUPO_NOMBRE]}, " +
                  f"Asignatura ID: {grupo[GRUPO_ID_ASIGNATURA]}, Asignatura: {nombre_asignatura}")
        print("--- FIN grupoS ACTUALES ---\n")


        # Verificar si hay asignaturas disponibles
        if not asignaturas_disponibles and not (not tiene_privada):
            mensaje = "⚠️ No hay más asignaturas disponibles para configurar."
            if tiene_privada:
                mensaje += "\n\nYa tienes una grupo configurada para cada asignatura y una grupo de tutoría privada."
            bot.send_message(chat_id, mensaje)
            return

        # Crear teclado con las asignaturas disponibles que no tienen grupo
        markup = types.InlineKeyboardMarkup()

        if asignaturas_disponibles:
            for asig in asignaturas_disponibles:
                callback_data = f"config_asig_{asig[MATRICULA_ID_ASIGNATURA]}"
                markup.add(types.InlineKeyboardButton(text=asig[MATRICULA_ASIGNATURA], callback_data=callback_data))

        # Añadir opción de tutoría privada SOLO si no tiene una ya
        if not tiene_privada:
            markup.add(types.InlineKeyboardButton("Tutoría Privada", callback_data="config_tutoria_privada"))
            print(f"✅ Usuario {user_id} NO tiene grupo privada - Mostrando opción")
        else:
            print(f"⚠️ Usuario {user_id} YA tiene grupo privada - Ocultando opción")

        # Comprobar si no hay opciones disponibles
        if not asignaturas_disponibles and tiene_privada:
            bot.send_message(
                chat_id,
                "⚠️ No puedes configurar más grupos. Ya tienes una grupo para cada asignatura y una grupo privada."
            )
            return

        # Guardar estado para manejar la siguiente interacción
        set_state(user_id, "esperando_asignatura_grupo")
        user_data[user_id] = {"chat_id": chat_id}

        # Enviar mensaje con las opciones
        mensaje = "🏫 *Configuración de grupo de tutoría*\n\n"

        if asignaturas_disponibles:
            mensaje += "Selecciona la asignatura para la que deseas configurar este grupo:"
        else:
            mensaje += "Ya has configurado grupos para todas tus asignaturas."

        # Si ya tiene grupo privada, informarle
        if tiene_privada:
            mensaje += "\n\n*Nota:* Ya tienes una grupo de tutoría privada configurada, por lo que esa opción no está disponible."

        bot.send_message(
            chat_id,
            mensaje,
            reply_markup=markup,
            parse_mode="Markdown"
        )


    @bot.callback_query_handler(func=lambda call: call.data.startswith('config_asig_'))
    def handle_configuracion_asignatura(call):
        user_id = call.from_user.id
        id_asignatura = call.data.split('_')[2]  # Extraer ID de la asignatura

        # Verificar estado
        if get_state(user_id) != "esperando_asignatura_grupo":
            bot.answer_callback_query(call.id, "Esta opción ya no está disponible")
            return

        # Obtener datos guardados
        if user_id not in user_data or "chat_id" not in user_data[user_id]:
            bot.answer_callback_query(call.id, "Error: Datos no encontrados")
            clear_state(user_id)
            return

        chat_id = user_data[user_id]["chat_id"]

        try:
            # Registrar el grupo en la base de datos
            # Obtener nombre de la asignatura
            asignatura_nombre = get_asignaturas(ASIGNATURA_ID=id_asignatura)[0][ASIGNATURA_NOMBRE]

            # Obtener Id_usuario del profesor a partir de su TelegramID
            id_usuario_profesor = get_usuarios(USUARIO_ID_TELEGRAM=str(user_id))[0][USUARIO_ID]

            # Cerrar la conexión temporal

            # Crear enlace de invitación si es posible
            try:
                enlace_invitacion = bot.create_chat_invite_link(chat_id).invite_link
            except:
                enlace_invitacion = None

            # Configurar directamente como grupo de avisos (pública)
            # CORRECCIÓN: Usar "pública" con tilde para cumplir con el constraint
            tipo_grupo = GRUPO_PUBLICO  # Cambiado de "publica" a "pública"
            grupo_tipo_texto = "Avisos"
            nuevo_nombre = f"{asignatura_nombre} - Avisos"

            # Cambiar el nombre del grupo
            try:
                bot.set_chat_title(chat_id, nuevo_nombre)
            except Exception as e:
                logger.warning(f"No se pudo cambiar el nombre del grupo: {e}")

            # Crear el grupo en la base de datos
            insert_grupo_tutoria(
                id_usuario_profesor,
                nuevo_nombre,
                tipo_grupo,  # Ahora con el valor correcto "pública"
                id_asignatura,
                str(chat_id),
                enlace_invitacion
            )

            # Mensaje de éxito
            bot.edit_message_text(
                f"✅ Grupo configurado exitosamente como grupo de avisos para *{asignatura_nombre}*",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="Markdown"
            )

            # Enviar mensaje informativo
            descripcion = "Esta es una grupo para **avisos generales** de la asignatura donde los estudiantes pueden unirse mediante el enlace de invitación."

            bot.send_message(
                chat_id,
                f"🎓 *grupo configurada*\n\n"
                f"Esta grupo está ahora configurada como: *grupo de Avisos*\n\n"
                f"{descripcion}\n\n"
                "Como profesor puedes:\n"
                "• Gestionar el grupo según el propósito configurado\n"
                "• Compartir el enlace de invitación con tus estudiantes",
                parse_mode="Markdown",
                reply_markup=menu_profesor()  # Esto ahora devuelve un ReplyKeyboardMarkup
            )

        except Exception as e:
            bot.send_message(chat_id, f"❌ Error al configurar grupo: {str(e)}")
            logger.error(f"Error en la selección de asignatura {chat_id}: {e}")

        # Limpiar estado
        clear_state(user_id)


    @bot.callback_query_handler(func=lambda call: call.data == 'config_tutoria_privada')
    def handle_configuracion_tutoria_privada(call):
        user_id = call.from_user.id

        # Verificar estado
        if get_state(user_id) != "esperando_asignatura_grupo":
            bot.answer_callback_query(call.id, "Esta opción ya no está disponible")
            return

        # Obtener datos guardados
        if user_id not in user_data or "chat_id" not in user_data[user_id]:
            bot.answer_callback_query(call.id, "Error: Datos no encontrados")
            clear_state(user_id)
            return

        chat_id = user_data[user_id]["chat_id"]

        try:
            # Registrar el grupo en la base de datos        
            # Obtener Id_usuario y nombre del profesor a partir de su TelegramID
            profesor = get_usuarios(USUARIO_ID_TELEGRAM=str(user_id))[0]
            id_usuario_profesor = profesor[USUARIO_ID]
            nombre_profesor = profesor[USUARIO_NOMBRE]


            # Crear enlace de invitación si es posible
            try:
                enlace_invitacion = bot.create_chat_invite_link(chat_id).invite_link
            except:
                enlace_invitacion = None

            # Configurar como grupo de tutorías privadas
            tipo_grupo = GRUPO_PRIVADO
            grupo_tipo_texto = "Tutoría Privada"
            nuevo_nombre = f"Tutoría Privada - Prof. {nombre_profesor}"

            # Cambiar el nombre del grupo
            try:
                bot.set_chat_title(chat_id, nuevo_nombre)
            except Exception as e:
                logger.warning(f"No se pudo cambiar el nombre del grupo: {e}")

            # Crear el grupo en la base de datos
            insert_grupo_tutoria(
                id_usuario_profesor,
                nuevo_nombre,
                tipo_grupo,
                "0",  # 0 indica que no está vinculado a una asignatura específica
                str(chat_id),
                enlace_invitacion
            )

            # Mensaje de éxito
            bot.edit_message_text(
                f"✅ Grupo configurado exitosamente como grupo de tutorías privadas",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="Markdown"
            )

            # Enviar mensaje informativo
            descripcion = "Esta es tu grupo de **tutorías privadas** donde solo pueden entrar estudiantes que invites específicamente."

            bot.send_message(
                chat_id,
                f"🎓 *grupo configurada*\n\n"
                f"Esta grupo está ahora configurada como: *grupo de Tutorías Privadas*\n\n"
                f"{descripcion}\n\n"
                "Como profesor puedes:\n"
                "• Invitar a estudiantes específicos para tutorías\n"
                "• Expulsar estudiantes cuando finalice la consulta",
                parse_mode="Markdown",
                reply_markup=menu_profesor()
            )

        except Exception as e:
            bot.send_message(chat_id, f"❌ Error al configurar grupo: {str(e)}")
            logger.error(f"Error en la configuración de tutoría privada {chat_id}: {e}")

        # Limpiar estado
        clear_state(user_id)


    @bot.message_handler(content_types=['group_chat_created'])
    def handle_group_creation(message):
        """Responde cuando se crea un nuevo grupo"""
        chat_id = message.chat.id

        print("\n==================================================")
        print(f"🆕🆕🆕 NUEVO GRUPO CREADO: {chat_id} 🆕🆕🆕")
        print(f"🆕 Creado por: {message.from_user.first_name} (ID: {message.from_user.id})")
        print("==================================================\n")

        bot.send_message(
            chat_id,
            "¡Gracias por crear un grupo con este bot!\n\n"
            "Para poder configurar correctamente el grupo necesito ser administrador. "
            "Por favor, sigue estos pasos:\n\n"
            "1. Entra en la información del grupo\n"
            "2. Selecciona 'Administradores'\n"
            "3. Añádeme como administrador\n"
            "4. Dame todos los permisos que me falten para ser adminsitrador.\n\n"
            "Una vez me hayas hecho administrador, usa el comando /configurar_grupo."
        )