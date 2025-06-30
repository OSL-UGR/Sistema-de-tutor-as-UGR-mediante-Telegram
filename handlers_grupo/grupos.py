import sys
import os
from db.queries import get_asignaturas, get_grupos_tutoria, get_grupos_tutoria, get_matriculas, get_usuarios, insert_grupo_tutoria, delete_grupo_tutoria, update_grupo_tutoria
# Añadir el directorio raíz al path para importar desde db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
from telebot import types
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ChatMemberHandler
import logging

# Estados para el flujo de conversación
ELEGIR_TIPO = 1
BUSCAR_ALUMNO = 2
SELECCIONAR_ALUMNO = 3
CONFIRMAR_EXPULSION = 4
SELECCIONAR_SALA = 5
CONFIRMAR_ELIMINAR_SALA = 6
SELECCIONAR_ASIGNATURA = 7
CONFIRMAR_CAMBIO = 8
CONFIRMAR_ELIMINAR_SALA_FINAL = 9

# Registro para evitar mensajes duplicados
ultimos_mensajes_bienvenida = {}
ultimas_acciones_admin = {}  # Para eventos de promoción a administrador

class GestionGrupos:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='logs/grupo_handlers.log', filemode='w')  
    
    def guardar_grupo(self, nombre_grupo: str, enlace_grupo: str, id_profesor: int, 
                      id_asignatura: int = None, es_tutoria: bool = False):
        """Guarda la información del grupo en la base de datos"""
        try:            
            # Determinar el tipo de sala según es_tutoria
            tipo_sala = 'privada' if es_tutoria else 'pública'
            
            # Extraer el chat_id del enlace o usar un valor único
            chat_id = enlace_grupo.split('/')[-1] if '/' in enlace_grupo else enlace_grupo
            
            inserted_id = insert_grupo_tutoria(id_profesor, nombre_grupo, tipo_sala, id_asignatura, chat_id, enlace_grupo)
            
            self.logger.info(f"Grupo guardado exitosamente: ID={inserted_id}, Nombre='{nombre_grupo}', " 
                             f"Profesor ID={id_profesor}, Asignatura ID={id_asignatura}, Es tutoria={es_tutoria}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error al guardar grupo '{nombre_grupo}': {e}")
            return False
    
    def verificar_salas_existentes(self, id_profesor):
        """
        Verifica qué salas ya tiene creadas el profesor
        Devuelve un diccionario con:
        - Lista de IDs de asignaturas con sala ya creada
        - Booleano indicando si ya tiene sala de tutorías
        """
        
        asignaturas_con_sala = [row["Id_asignatura"] for row in get_grupos_tutoria(profesor_id=id_profesor, tipo_sala="publica")]
        
        tiene_sala_tutoria = get_grupos_tutoria(profesor_id=id_profesor, tipo_sala="privada")[0] is not None
                
        return {
            'asignaturas_con_sala': asignaturas_con_sala,
            'tiene_sala_tutoria': tiene_sala_tutoria
        }
    

    
    def procesar_eleccion(self, update: Update, context: CallbackContext) -> int:
        """Procesa la elección del profesor sobre el tipo de sala"""
        query = update.callback_query
        query.answer()
        
        eleccion = query.data
        id_profesor = context.user_data.get('id_profesor')
        nombre_grupo = context.user_data.get('grupo_nombre')
        enlace_grupo = context.user_data.get('grupo_enlace')
        
        if not all([id_profesor, nombre_grupo, enlace_grupo]):
            query.edit_message_text("Ocurrió un error al procesar la información del grupo.")
            return ConversationHandler.END
        
        if eleccion == "tutoria":
            # Es una sala de tutorías
            self.guardar_grupo(nombre_grupo, enlace_grupo, id_profesor, None, True)
            query.edit_message_text(f"El grupo '{nombre_grupo}' ha sido configurado como tu sala de tutorías individuales.")
        else:
            # Es una sala de asignatura
            asignatura_id = int(eleccion.split('_')[1])
            self.guardar_grupo(nombre_grupo, enlace_grupo, id_profesor, asignatura_id, False)
            
            # Obtener nombre de la asignatura
            nombre_asignatura = get_asignaturas(Id_asignatura=asignatura_id)[0]["Nombre"]
            
            query.edit_message_text(
                f"El grupo '{nombre_grupo}' ha sido asociado a la asignatura '{nombre_asignatura}'.\n\n"
                "Si en el futuro necesitas cambiar la asignatura asociada, puedes usar el comando /cambiar_asignatura"
            )
        
        return ConversationHandler.END
    
    def es_sala_tutoria(self, id_chat):
        """Verifica si un chat es una sala de tutoría"""
        
        result = get_grupos_tutoria(Chat_id=id_chat)[0]["Tipo_sala"]
        
        return result and result[0] == 'privada'
    
    def es_profesor(self, user_id):
        """Verifica si un usuario es profesor"""
        result = get_usuarios(TelegramID=user_id)[0]["Tipo"]
        
        return result and result[0] == 'profesor'
    
    def finalizar_sesion(self, update: Update, context: CallbackContext) -> int:
        """Gestiona el comando /finalizar tanto para profesores como para alumnos"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Verificar que sea una sala de tutoría
        if not self.es_sala_tutoria(chat_id):
            update.message.reply_text("Esta función solo está disponible en salas de tutoría individuales.")
            return ConversationHandler.END
        
        # Comportamiento diferente según el rol
        if self.es_profesor(user_id):
            # Es profesor: mostrar lista de alumnos para expulsar
            return self.iniciar_expulsion_por_profesor(update, context)
        else:
            # Es alumno: autoexpulsión
            return self.autoexpulsion_alumno(update, context)
    
    def autoexpulsión_alumno(self, update: Update, context: CallbackContext) -> int:
        """Permite a un alumno salir del grupo voluntariamente"""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        try:
            # Obtener el nombre del alumno
            nombre = update.effective_user.first_name
            if update.effective_user.last_name:
                nombre += f" {update.effective_user.last_name}"
            
            # Expulsar al usuario que solicitó salir (ban temporal de 1 minuto)
            until_date = int(time.time()) + 60
            context.bot.ban_chat_member(chat_id, user_id, until_date=until_date)
            
            # Enviar mensaje privado al usuario
            context.bot.send_message(
                chat_id=user_id, 
                text="Has finalizado tu sesión de tutoría. Gracias por participar."
            )
            
            # Informar al grupo
            update.message.reply_text(
                f"{nombre} ha finalizado su sesión de tutoría."
            )
            
        except Exception as e:
            self.logger.error(f"Error en autoexpulsión: {e}")
            update.message.reply_text("No pude procesar tu solicitud para finalizar la sesión.")
        
        return ConversationHandler.END
    
    def iniciar_expulsion_por_profesor(self, update: Update, context: CallbackContext) -> int:
        """Inicia el proceso para que un profesor expulse a un alumno"""
        chat_id = update.effective_chat.id
        
        # Guardar el chat_id en el contexto para usarlo más tarde
        context.user_data['chat_id'] = chat_id
        
        try:
            # Obtener lista de miembros del chat
            chat_members = context.bot.get_chat_administrators(chat_id)
            admin_ids = [member.user.id for member in chat_members]
            
            # Intentar obtener todos los miembros (esto podría ser limitado por la API)
            all_members = []
            for member in context.bot.get_chat_members(chat_id):
                if member.user.id not in admin_ids:
                    all_members.append(member)
            
            if not all_members:
                update.message.reply_text("No hay alumnos en este grupo.")
                return ConversationHandler.END
            
            # Preguntar si quiere buscar por nombre o ver la lista completa
            keyboard = [
                [InlineKeyboardButton("Buscar por nombre", callback_data="buscar")],
                [InlineKeyboardButton("Ver lista completa", callback_data="lista")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(
                "¿Cómo quieres seleccionar al alumno cuya sesión deseas finalizar?", 
                reply_markup=reply_markup
            )
            
            # Guardar la lista de miembros en el contexto
            context.user_data['miembros'] = all_members
            return BUSCAR_ALUMNO
            
        except Exception as e:
            self.logger.error(f"Error al obtener miembros: {e}")
            update.message.reply_text(
                "No pude obtener la lista de miembros del grupo. "
                "Asegúrate de que tengo los permisos necesarios."
            )
            return ConversationHandler.END
    
    def procesar_opcion_busqueda(self, update: Update, context: CallbackContext) -> int:
        """Procesa la elección del método de búsqueda"""
        query = update.callback_query
        query.answer()
        
        if query.data == "buscar":
            query.edit_message_text("Por favor, envía el nombre o parte del nombre del alumno a buscar:")
            return SELECCIONAR_ALUMNO
        else:
            # Mostrar lista completa de alumnos
            miembros = context.user_data.get('miembros', [])
            keyboard = []
            
            for i, miembro in enumerate(miembros):
                nombre = miembro.user.first_name
                if miembro.user.last_name:
                    nombre += f" {miembro.user.last_name}"
                keyboard.append([InlineKeyboardButton(nombre, callback_data=f"user_{miembro.user.id}")])
            
            # Añadir botón de cancelar
            keyboard.append([InlineKeyboardButton("Cancelar", callback_data="cancelar")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text("Selecciona el alumno cuya sesión deseas finalizar:", reply_markup=reply_markup)
            
            return CONFIRMAR_EXPULSION
    
    def buscar_alumno(self, update: Update, context: CallbackContext) -> int:
        """Busca alumnos por nombre"""
        texto_busqueda = update.message.text.lower()
        miembros = context.user_data.get('miembros', [])
        
        # Filtrar miembros por nombre
        miembros_filtrados = []
        for miembro in miembros:
            nombre = miembro.user.first_name.lower()
            if miembro.user.last_name:
                nombre += f" {miembro.user.last_name.lower()}"
            
            if texto_busqueda in nombre:
                miembros_filtrados.append(miembro)
        
        if not miembros_filtrados:
            update.message.reply_text("No se encontraron alumnos con ese nombre. Intenta con otro término.")
            return SELECCIONAR_ALUMNO
        
        # Mostrar resultados
        keyboard = []
        for miembro in miembros_filtrados:
            nombre = miembro.user.first_name
            if miembro.user.last_name:
                nombre += f" {miembro.user.last_name}"
            keyboard.append([InlineKeyboardButton(nombre, callback_data=f"user_{miembro.user.id}")])
        
        # Añadir botón de cancelar
        keyboard.append([InlineKeyboardButton("Cancelar", callback_data="cancelar")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Selecciona el alumno cuya sesión deseas finalizar:", reply_markup=reply_markup)
        
        return CONFIRMAR_EXPULSION
    
    def confirmar_expulsion(self, update: Update, context: CallbackContext) -> int:
        """Confirma la expulsión de un alumno"""
        query = update.callback_query
        query.answer()
        
        if query.data == "cancelar":
            query.edit_message_text("Operación cancelada.")
            return ConversationHandler.END
        
        user_id = int(query.data.split("_")[1])
        chat_id = context.user_data.get('chat_id')
        
        try:
            # Obtener información del usuario
            miembro = next((m for m in context.user_data.get('miembros', []) 
                         if m.user.id == user_id), None)
            
            if not miembro:
                query.edit_message_text("No pude encontrar al usuario seleccionado.")
                return ConversationHandler.END
                
            nombre = miembro.user.first_name
            if miembro.user.last_name:
                nombre += f" {miembro.user.last_name}"
                
            # Guardar datos para la expulsión
            context.user_data['expulsar_id'] = user_id
            context.user_data['expulsar_nombre'] = nombre
            
            # Pedir confirmación
            keyboard = [
                [InlineKeyboardButton("Confirmar", callback_data="confirm")],
                [InlineKeyboardButton("Cancelar", callback_data="cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(
                f"¿Estás seguro de finalizar la sesión de {nombre}?",
                reply_markup=reply_markup
            )
            
            return CONFIRMAR_EXPULSION
            
        except Exception as e:
            self.logger.error(f"Error al preparar expulsión: {e}")
            query.edit_message_text("Ocurrió un error al procesar la solicitud.")
            return ConversationHandler.END
    
    def ejecutar_expulsion(self, update: Update, context: CallbackContext) -> int:
        """Ejecuta la expulsión del alumno"""
        query = update.callback_query
        query.answer()
        
        if query.data == "cancel":
            query.edit_message_text("Operación cancelada.")
            return ConversationHandler.END
        
        chat_id = context.user_data.get('chat_id')
        user_id = context.user_data.get('expulsar_id')
        nombre = context.user_data.get('expulsar_nombre')
        
        try:
            # Expulsar al usuario por 1 minuto (60 segundos)
            until_date = int(time.time()) + 60
            context.bot.ban_chat_member(chat_id, user_id, until_date=until_date)
            
            # Informar al profesor que la expulsión fue exitosa
            query.edit_message_text(f"Has finalizado la sesión de tutoría con {nombre}.")
            
            # Informar en el grupo 
            context.bot.send_message(
                chat_id=chat_id,
                text=f"El profesor ha finalizado la sesión de tutoría con {nombre}."
            )
            
            # Intentar enviar mensaje privado al alumno
            try:
                context.bot.send_message(
                    chat_id=user_id,
                    text="El profesor ha finalizado tu sesión de tutoría. Gracias por participar."
                )
            except:
                # Si no podemos enviar mensaje al alumno, lo ignoramos
                pass
            
            return ConversationHandler.END
            
        except Exception as e:
            self.logger.error(f"Error al expulsar: {e}")
            query.edit_message_text("No pude finalizar la sesión. Asegúrate de que soy administrador con permisos suficientes.")
            return ConversationHandler.END
    
    def cambiar_asignatura_sala(self, update: Update, context: CallbackContext) -> int:
        """Permite al profesor cambiar la asignatura asociada a una sala"""
        user_id = update.effective_user.id
        
        # Verificar que sea profesor
        if not self.es_profesor(user_id):
            update.message.reply_text("Solo los profesores pueden usar esta función.")
            return ConversationHandler.END
        
        # Obtener salas del profesor     
        salas = get_grupos_tutoria(Id_usuario = user_id, tipo_sala="pública")

        if not salas:
            update.message.reply_text("No tienes salas de asignatura configuradas.")
            return ConversationHandler.END
        
        # Mostrar lista de salas para seleccionar
        keyboard = []
        for sala in salas:
            keyboard.append([
                InlineKeyboardButton(
                    f"{sala["Nombre_Sala"]} - {sala["Asignatura"] or 'Sin asignatura'}", 
                    callback_data=f"sala_{sala['id_sala']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("Cancelar", callback_data="cancelar")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "Selecciona la sala a la que quieres cambiar la asignatura:",
            reply_markup=reply_markup
        )
        
        # Guardar salas en contexto
        context.user_data['salas'] = {sala[0]: sala for sala in salas}
        
        return SELECCIONAR_SALA
    
    def eliminar_sala(self, update: Update, context: CallbackContext) -> int:
        """Permite al profesor eliminar una sala de la base de datos"""
        user_id = update.effective_user.id
        
        # Verificar que sea profesor
        if not self.es_profesor(user_id):
            update.message.reply_text("Solo los profesores pueden usar esta función.")
            return ConversationHandler.END
        
        # Obtener salas del profesor        
        salas = get_grupos_tutoria(Id_usuario=user_id)
        
        if not salas:
            update.message.reply_text("No tienes salas configuradas.")
            return ConversationHandler.END
        
        # Mostrar lista de salas para eliminar
        keyboard = []
        for sala in salas:
            if (sala["Tipo_sala"] == "privada"):
                keyboard.append([
                    InlineKeyboardButton(
                        f"{salas["Nombre_sala"]} - {'Sala de Tutorías'}", 
                        callback_data=f"eliminar_{sala['id_sala']}"
                    )
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{sala['Nombre_sala']} - {sala['Asignatura'] or 'Sin asignatura'}", 
                        callback_data=f"eliminar_{sala['id_sala']}"
                    )
                ])
        
        keyboard.append([InlineKeyboardButton("Cancelar", callback_data="cancelar")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "⚠️ ATENCIÓN: Al eliminar una sala, se perderá su configuración en el sistema.\n"
            "Esto NO eliminará el grupo de Telegram, solo su vinculación con tus asignaturas.\n\n"
            "Selecciona la sala que quieres eliminar:",
            reply_markup=reply_markup
        )
        
        return CONFIRMAR_ELIMINAR_SALA
    
    def procesar_cambio_asignatura(self, update: Update, context: CallbackContext) -> int:
        """Procesa la selección de sala para cambiar su asignatura"""
        query = update.callback_query
        query.answer()
        
        if query.data == "cancelar":
            query.edit_message_text("Operación cancelada.")
            return ConversationHandler.END
        
        # Obtener ID de la sala seleccionada
        sala_id = int(query.data.split('_')[1])
        sala_info = context.user_data.get('salas', {}).get(sala_id)
        
        if not sala_info:
            query.edit_message_text("No se encontró información sobre la sala seleccionada.")
            return ConversationHandler.END
        
        # Guardar información de la sala en el contexto
        context.user_data['sala_actual'] = {
            'id': sala_id,
            'nombre': sala_info[1],  # nombre_sala
            'asignatura_actual': sala_info[3]  # id_asignatura
        }
        
        # Obtener asignaturas disponibles para el profesor
        user_id = update.effective_user.id
        asignaturas = get_matriculas(Id_usuario=user_id)
        
        # Crear teclado con opciones de asignaturas
        keyboard = []
        for asig in asignaturas:
            id_asig = asig["Id_asignatura"]
            if id_asig != sala_info[3]:  # No mostrar la asignatura actual
                keyboard.append([InlineKeyboardButton(asig["Asignatura"], callback_data=f"asignar_{id_asig}")])        
        keyboard.append([InlineKeyboardButton("Cancelar", callback_data="cancelar")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Mostrar opciones
        query.edit_message_text(
            f"Selecciona la nueva asignatura para la sala '{sala_info[1]}':",
            reply_markup=reply_markup
        )
        
        # Añadir un estado adicional para seleccionar la nueva asignatura
        return SELECCIONAR_ASIGNATURA

    def confirmar_cambio_asignatura(self, update: Update, context: CallbackContext) -> int:
        """Confirma el cambio de asignatura y pregunta si expulsar a los miembros"""
        query = update.callback_query
        query.answer()
        
        if query.data == "cancelar":
            query.edit_message_text("Operación cancelada.")
            return ConversationHandler.END
        
        # Obtener la nueva asignatura seleccionada
        nueva_asignatura_id = int(query.data.split('_')[1])
        
        # Obtener nombre de la asignatura
        nombre_asignatura = get_asignaturas(Id_asignatura=nueva_asignatura_id)[0]["Nombre"]
        
        # Guardar en el contexto
        context.user_data['nueva_asignatura'] = {
            'id': nueva_asignatura_id,
            'nombre': nombre_asignatura
        }
        
        # Confirmar y preguntar sobre expulsión de miembros
        sala_nombre = context.user_data['sala_actual']['nombre']
        keyboard = [
            [InlineKeyboardButton("Cambiar y mantener miembros", callback_data="cambiar_mantener")],
            [InlineKeyboardButton("Cambiar y expulsar miembros", callback_data="cambiar_expulsar")],
            [InlineKeyboardButton("Cancelar", callback_data="cancelar")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            f"¿Confirmas cambiar la sala '{sala_nombre}' a la asignatura '{nombre_asignatura}'?\n\n"
            "¿Qué deseas hacer con los miembros actuales del grupo?",
            reply_markup=reply_markup
        )
        
        return CONFIRMAR_CAMBIO

    def ejecutar_cambio_asignatura(self, update: Update, context: CallbackContext) -> int:
        """Ejecuta el cambio de asignatura y expulsa miembros si es necesario"""
        query = update.callback_query
        query.answer()
        
        expulsar_miembros = (query.data == "cambiar_expulsar")
        sala_id = context.user_data['sala_actual']['id']
        nueva_asignatura_id = context.user_data['nueva_asignatura']['id']
        sala_nombre = context.user_data['sala_actual']['nombre']
        nueva_asignatura_nombre = context.user_data['nueva_asignatura']['nombre']
        
        # Actualizar la asignatura en la base de datos        
        try:
            # Obtener el chat_id de la sala
            chat_id = get_grupos_tutoria(id_sala=sala_id)[0]["Chat_id"]
            
            if not chat_id:
                query.edit_message_text("No se encontró la sala en la base de datos.")
                return ConversationHandler.END
            
            # Actualizar la asignatura
            update_grupo_tutoria(sala_id, Id_asignatura=nueva_asignatura_id)
            
            # Si se solicitó expulsar miembros, hacerlo
            if expulsar_miembros:
                self.expulsar_todos_miembros(context.bot, chat_id, exclude_admins=True)
                mensaje_resultado = (
                    f"La sala '{sala_nombre}' ha sido asignada a la asignatura '{nueva_asignatura_nombre}'.\n"
                    "Todos los miembros han sido expulsados del grupo."
                )
            else:
                mensaje_resultado = (
                    f"La sala '{sala_nombre}' ha sido asignada a la asignatura '{nueva_asignatura_nombre}'.\n"
                    "Los miembros actuales se han mantenido en el grupo."
                )
            
            query.edit_message_text(mensaje_resultado)
            
        except Exception as e:
            self.logger.error(f"Error al cambiar asignatura: {e}")
            query.edit_message_text("Ocurrió un error al cambiar la asignatura de la sala.")
    
        return ConversationHandler.END

    def expulsar_todos_miembros(self, bot, chat_id, exclude_admins=True):
        """Expulsa a todos los miembros de un grupo excepto administradores"""
        try:
            # Obtener lista de administradores
            admins = []
            if exclude_admins:
                admins = [member.user.id for member in bot.get_chat_administrators(chat_id)]
            
            # Añadir el ID del bot para no auto-expulsarse
            bot_id = bot.get_me().id
            if bot_id not in admins:
                admins.append(bot_id)
            
            # Obtener todos los miembros y expulsar a los que no son admin
            chat_members = bot.get_chat_members(chat_id)
            expulsados = 0
            
            for member in chat_members:
                if member.user.id not in admins:
                    # Ban temporal (1 minuto)
                    until_date = int(time.time()) + 60
                    bot.ban_chat_member(chat_id, member.user.id, until_date=until_date)
                    expulsados += 1
                    
                    # Intentar enviar mensaje al usuario expulsado
                    try:
                        bot.send_message(
                            chat_id=member.user.id,
                            text="Has sido expulsado del grupo porque la configuración del mismo ha cambiado."
                        )
                    except:
                        # Si no podemos enviar mensaje al usuario, lo ignoramos
                        pass
            
            # Enviar mensaje al grupo
            if expulsados > 0:
                bot.send_message(
                    chat_id=chat_id,
                    text=f"La configuración de este grupo ha cambiado. Se han expulsado {expulsados} miembros."
                )
                
            return expulsados
        
        except Exception as e:
            self.logger.error(f"Error al expulsar miembros: {e}")
            return 0

    def ejecutar_eliminar_sala(self, update: Update, context: CallbackContext) -> int:
        """Elimina una sala y opcionalmente expulsa a sus miembros"""
        query = update.callback_query
        query.answer()
        
        if query.data == "cancelar":
            query.edit_message_text("Operación cancelada.")
            return ConversationHandler.END
        
        # Obtener ID de la sala
        sala_id = int(query.data.split('_')[1])
        
        # Obtener información de la sala        
        try:
            sala_info = get_grupos_tutoria(id_sala=sala_id)[0]
            
            if not sala_info:
                query.edit_message_text("No se encontró información sobre la sala seleccionada.")
                return ConversationHandler.END
            
            nombre_sala = sala_info["Nombre_sala"]  # Nombre de la sala
            chat_id = sala_info["Chat_id"]  # ID del chat del grupo
            if sala_info["Tipo_sala"] == "privada":
                tipo_sala = "Sala de Tutorías"
            else:   
                tipo_sala = sala_info["Asignatura"] if sala_info["Asignatura"] else "Sin asignatura"
            
            # Preguntar si quiere expulsar a todos los miembros
            keyboard = [
                [InlineKeyboardButton("Eliminar y expulsar miembros", callback_data=f"expulsar_{sala_id}")],
                [InlineKeyboardButton("Solo eliminar configuración", callback_data=f"soloeliminar_{sala_id}")],
                [InlineKeyboardButton("Cancelar", callback_data="cancelar")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                f"¿Confirmas eliminar la sala '{nombre_sala}' ({tipo_sala})?\n\n"
                "¿Qué deseas hacer con los miembros actuales del grupo?",
                reply_markup=reply_markup
            )
            
            # Guardar información para el siguiente paso
            context.user_data['sala_eliminar'] = {
                'id': sala_id,
                'nombre': nombre_sala,
                'tipo': tipo_sala,
                'chat_id': chat_id
            }
            
            return CONFIRMAR_ELIMINAR_SALA_FINAL
            
        except Exception as e:
            self.logger.error(f"Error al preparar eliminación de sala: {e}")
            query.edit_message_text("Ocurrió un error al procesar la solicitud.")
            return ConversationHandler.END

    
    
    def confirmar_eliminar_sala_final(self, update: Update, context: CallbackContext) -> int:
        """Confirmación final y ejecución de la eliminación de sala"""
        query = update.callback_query
        query.answer()
        
        if query.data == "cancelar":
            query.edit_message_text("Operación cancelada.")
            return ConversationHandler.END
        
        accion, sala_id = query.data.split('_')
        sala_id = int(sala_id)
        
        # Verificar que coincida con la sala almacenada
        if context.user_data.get('sala_eliminar', {}).get('id') != sala_id:
            query.edit_message_text("Error de validación. Inténtalo de nuevo.")
            return ConversationHandler.END
        
        sala_info = context.user_data['sala_eliminar']
        expulsar_miembros = (accion == "expulsar")
        
        # Eliminar sala de la base de datos
        
        
        try:
            # Eliminar de la BD
            delete_grupo_tutoria(sala_id)
            
            # Si se solicitó expulsar miembros, hacerlo
            if expulsar_miembros and sala_info['chat_id']:
                expulsados = self.expulsar_todos_miembros(context.bot, sala_info['chat_id'])
                mensaje_resultado = (
                    f"La sala '{sala_info['nombre']}' ({sala_info['tipo']}) ha sido eliminada del sistema.\n"
                    f"Se han expulsado {expulsados} miembros del grupo."
                )
            else:
                mensaje_resultado = (
                    f"La sala '{sala_info['nombre']}' ({sala_info['tipo']}) ha sido eliminada del sistema.\n"
                    "No se ha expulsado a ningún miembro del grupo."
                )
            
            query.edit_message_text(mensaje_resultado)
            
        except Exception as e:
            self.logger.error(f"Error al eliminar sala: {e}")
            query.edit_message_text("Ocurrió un error al eliminar la sala.")
        
        return ConversationHandler.END

    def registrar_handlers(self, bot):
        """Registra los handlers necesarios para la gestión de grupos en telebot"""
        
        print("\n==================================================")
        print("🔧🔧🔧 REGISTRANDO HANDLERS DE GESTION_GRUPOS 🔧🔧🔧")
        print("==================================================\n")
        
        # IMPORTANTE: ELIMINAR cualquier handler de new_chat_members aquí
        # para que no entre en conflicto con el que ya está definido en bot_grupo_main.py
        
        # Comandos
        @bot.message_handler(commands=['finalizar'])
        def finalizar_handler(message):
            print("🔄 Comando finalizar recibido")
            self.finalizar_sesion(message)
        
        @bot.message_handler(commands=['eliminar_sala'])
        def eliminar_sala_handler(message):
            print("🔄 Comando eliminar_sala recibido")
            self.eliminar_sala(message)
        
        @bot.message_handler(commands=['cambiar_asignatura'])
        def cambiar_asignatura_handler(message):
            print("🔄 Comando cambiar_asignatura recibido")
            self.cambiar_asignatura_sala(message)
        
        # IMPORTANTE: NO registrar un handler para new_chat_members aquí
        # Ya que está definido en bot_grupo_main.py
        
        # Callbacks
        @bot.callback_query_handler(func=lambda call: call.data.startswith("eliminar_"))
        def ejecutar_eliminar_sala_handler(call):
            self.ejecutar_eliminar_sala(call)
        
        @bot.callback_query_handler(func=lambda call: call.data == "cancelar")
        def cancelar_handler(call):
            bot.answer_callback_query(call.id, "Operación cancelada")
        
        # Más callbacks según necesites
        @bot.callback_query_handler(func=lambda call: call.data.startswith("sala_"))
        def seleccionar_sala_handler(call):
            self.procesar_cambio_asignatura(call, bot)
        
        @bot.callback_query_handler(func=lambda call: call.data.startswith("asignar_"))
        def asignar_handler(call):
            self.confirmar_cambio_asignatura(call, bot)
        
        @bot.callback_query_handler(func=lambda call: call.data.startswith("cambiar_"))
        def confirmar_cambio_handler(call):
            self.ejecutar_cambio_asignatura(call, bot)
