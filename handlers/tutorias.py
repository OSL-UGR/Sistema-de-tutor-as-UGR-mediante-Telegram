import telebot
from telebot import types
import sys
import os
import datetime
import time  # Faltaba esta importación
import logging  # Para usar logger

# Importar esta función al principio del archivo

# Configurar logger
logger = logging.getLogger(__name__)

# Añadir directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.queries import (
    get_grupos_tutoria,
    get_matriculas,
    get_usuarios,
    get_usuarios_by_multiple_ids,
)
from db.constantes import *

COMMAND_TUTORIA ='tutoria'

# Calldata
SOLICITAR_GRUPO = "solicitar_grupo_"
APROBAR_TUTORIA = "aprobar_tutoria_"
RECHAZAR_TUTORIA = "rechazar_tutoria_"


#Campos estructuras internas de datos

GENERAL = "general"


def register_handlers(bot):
    """Registra todos los handlers de tutorías"""
    
    @bot.message_handler(commands=[COMMAND_TUTORIA])
    def handle_tutoria_command(message):
        """Muestra profesores y grupos disponibles para las asignaturas del estudiante"""
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        print(f"\n### INICIO COMANDO TUTORIA ###")
        print(f"Usuario ID: {user_id}, Chat ID: {chat_id}")
        
        # Obtener información del usuario
        user = get_usuarios(USUARIO_ID_TELEGRAM=user_id)[0]
        
        # Diagnóstico: Verificar si hay grupos en la base de datos        
        # Contar todas las grupos
        grupos = get_grupos_tutoria()
        print(f"Total de grupos en la BD: {len(grupos)}")
        
        # Mostrar detalles de algunas grupos para diagnóstico
        if len(grupos) > 0:            
            print("Primeras 5 grupos en la BD:")
            for grupo in grupos[:5]:
                print(f"  - ID: {grupo[GRUPO_ID]}, Nombre: {grupo[GRUPO_NOMBRE]}")
                print(f"    Profesor: {grupo[GRUPO_ID_USUARIO]}, Asignatura: {grupo[GRUPO_ID_ASIGNATURA]} ({grupo[GRUPO_ASIGNATURA]})")
                print(f"    Tipo: {grupo[GRUPO_TIPO]}, Propósito: {grupo[GRUPO_PROPOSITO]}")
                print("    ---")
        
        if not user:
            bot.send_message(chat_id, "❌ No estás registrado. Usa /start para registrarte.")
            print("❌ Usuario no registrado")
            return
        
        if user[USUARIO_TIPO] != USUARIO_TIPO_ESTUDIANTE:
            bot.send_message(chat_id, "⚠️ Esta funcionalidad está disponible solo para estudiantes.")
            print("⚠️ Usuario no es estudiante")
            return
        
        print(f"✅ Estudiante: {user[USUARIO_NOMBRE]} {user[USUARIO_APELLIDOS] or ''}")
        
        # Obtener las asignaturas del estudiante        
        asignaturas = get_matriculas(MATRICULA_ID_USUARIO=user[USUARIO_ID])
        
        if not asignaturas:
            bot.send_message(chat_id, "❌ No estás matriculado en ninguna asignatura.")
            print("❌ Estudiante sin asignaturas")
            return
        
        print(f"✅ Asignaturas encontradas: {len(asignaturas)}")
        
        # Obtener IDs de asignaturas para usar en consultas
        asignaturas_ids = [a[ASIGNATURA_ID] for a in asignaturas]

        matriculas_profesores = get_matriculas(MATRICULA_TIPO=MATRICULA_PROFESOR)
        profesores_ids = [m[MATRICULA_ID_USUARIO] for m in matriculas_profesores if m[MATRICULA_ID_ASIGNATURA] in asignaturas_ids]
        
        # Obtener profesores que son de estas asignaturas según las matrículas (donde son docentes)
        profesores_raw = get_usuarios_by_multiple_ids(profesores_ids)
        print(f"✅ Profesores encontrados: {len(profesores_raw)}")
        
        # Convertir a diccionario para facilitar el acceso
        profesores = {}
        for profesor in profesores_raw:
            prof_id = profesor[USUARIO_ID]
            profesores[prof_id] = {
                USUARIO_ID: prof_id,
                USUARIO_NOMBRE: f"{profesor[USUARIO_NOMBRE]} {profesor[USUARIO_APELLIDOS] or ''}".strip(),
                USUARIO_EMAIL: profesor[USUARIO_EMAIL],
                USUARIO_HORARIO: profesor[USUARIO_HORARIO] or 'No especificado',
                MATRICULAS: {}
            }
        
        # Obtener asignaturas por profesor (basado en matrículas de tipo 'docente' y en grupos creados)
        for profesor_id in profesores:
            # Buscar asignaturas por matrículas donde es docente
            asignaturas_profesor = get_matriculas(MATRICULA_TIPO=MATRICULA_PROFESOR, MATRICULA_ID_USUARIO=profesor_id)
            asignaturas_alumno_profesor = []

            for asig in asignaturas_profesor:
                if asig[MATRICULA_ID_ASIGNATURA] in asignaturas_ids:
                    asignaturas_alumno_profesor.append(asig)
            
            for asig in asignaturas_alumno_profesor:
                if asig[MATRICULA_ID_ASIGNATURA] is not None:  # Si la asignatura existe
                    profesores[profesor_id][MATRICULAS][asig[MATRICULA_ID_ASIGNATURA]] = {
                        ASIGNATURA_ID: asig[MATRICULA_ID_ASIGNATURA],
                        ASIGNATURA_NOMBRE: asig[MATRICULA_ASIGNATURA],
                        ASIGNATURA_CODIGO: asig[MATRICULA_CODIGO],
                        GRUPOS: []

                    }
        
        # Inicializar la categoría general para cada profesor
        for profesor_id in profesores:
            profesores[profesor_id][MATRICULAS][GENERAL] = {
                ASIGNATURA_ID: GENERAL,
                ASIGNATURA_NOMBRE: 'General',
                GRUPOS: []
            }
        
        # Obtener todas las grupos de cada profesor
        for profesor_id in profesores:
            grupos = get_grupos_tutoria(GRUPO_ID_USUARIO=profesor_id)
            print(f"Encontradas {len(grupos)} grupos para el profesor {profesor_id}")
            
            # Clasificar las grupos por asignatura
            for grupo in grupos:
                grupo_data = {                                 
                    GRUPO_ID: grupo[GRUPO_ID],
                    GRUPO_NOMBRE: grupo[GRUPO_NOMBRE],
                    GRUPO_PROPOSITO: grupo[GRUPO_PROPOSITO],
                    GRUPO_TIPO: grupo[GRUPO_TIPO],
                    GRUPO_ENLACE: grupo[GRUPO_ENLACE],
                    GRUPO_ID_CHAT: grupo[GRUPO_ID_CHAT],
                    GRUPO_ASIGNATURA: grupo[GRUPO_ASIGNATURA],
                }
                
                # Asignar la grupo a su asignatura correspondiente (o a general si no tiene)
                if grupo[GRUPO_ID_ASIGNATURA] is not None:
                    asignatura_id = grupo[GRUPO_ID_ASIGNATURA]
                    # Verificar que la asignatura existe en el diccionario del profesor
                    if asignatura_id in profesores[profesor_id][MATRICULAS]:
                        profesores[profesor_id][MATRICULAS][asignatura_id][GRUPOS].append(grupo_data)
                        print(f"Asignada grupo '{grupo[GRUPO_NOMBRE]}' a asignatura ID {asignatura_id}")
                    else:
                        # Si por alguna razón la asignatura no está en el diccionario, asignar a general
                        profesores[profesor_id][MATRICULAS][GENERAL][GRUPOS].append(grupo_data)
                        print(f"grupo '{grupo[GRUPO_NOMBRE]}' asignada a GENERAL (asignatura ID {asignatura_id} no encontrada)")
                else:
                    # Si la grupo no tiene asignatura, agregarla a la categoría "general"
                    profesores[profesor_id][MATRICULAS][GENERAL][GRUPOS].append(grupo_data)
                    print(f"grupo '{grupo[GRUPO_NOMBRE]}' asignada a GENERAL (sin asignatura asociada)")

        
        # Si no se encontró ningún profesor, mostrar mensaje y terminar
        if not profesores:
            bot.send_message(chat_id, "❌ No se encontraron profesores para tus asignaturas.")
            return
        
        # Mejorar la parte que genera el mensaje y muestra las grupos
        for profesor_id, prof_info in profesores.items():
            # Sección del profesor
            mensaje = f"👨‍🏫 *Profesor: {prof_info[USUARIO_NOMBRE]}*\n"
            mensaje += f"📧 Email: {prof_info[USUARIO_EMAIL]}\n"
            mensaje += f"🕗 Horario:"

            dias = prof_info[USUARIO_HORARIO].split(', ')
            
            dia_anterior = ""
            for dia in dias:
                dia = dia.split(' ')
                if dia[0] != dia_anterior:
                    mensaje += f"\n  -{dia[0]} {dia[1]}"
                else:
                    mensaje += f", {dia[1]}"
                dia_anterior = dia[0]
                

            mensaje += "\n\n"
            
            markup = types.InlineKeyboardMarkup()  # Crear markup para botones
            
            # Recopilar todas las grupos del profesor desde todas las asignaturas
            todas_las_grupos = []
            for asignatura_id, asignatura in prof_info[MATRICULAS].items():
                if GRUPOS in asignatura:
                    print(asignatura)
                    for grupo in asignatura[GRUPOS]:
                        grupo[GRUPO_ID_ASIGNATURA] = asignatura_id
                        grupo[GRUPO_ASIGNATURA] = asignatura[ASIGNATURA_NOMBRE]
                        todas_las_grupos.append(grupo)
            
            print(f"Total grupos para profesor {profesor_id}: {len(todas_las_grupos)}")
            
            # Primero mostrar las asignaturas que imparte
            mensaje += "📚 *Asignaturas:*\n"
            
            # Variable para controlar si hay grupos privados
            grupos_privados = []
            
            for asignatura_id, asignatura in prof_info[MATRICULAS].items():
                if asignatura_id != GENERAL:  # Solo las asignaturas regulares, no la categoría "general"
                    nombre = asignatura[ASIGNATURA_NOMBRE]
                    codigo = asignatura.get(ASIGNATURA_CODIGO, '') or ''
                    
                    # Mostrar información de la asignatura
                    mensaje += f"• {nombre}"
                    if codigo:
                        mensaje += f" ({codigo})"
                    mensaje += "\n"
                    
                    # Filtrar grupos para esta asignatura específica
                    grupos_asignatura = [s for s in asignatura.get(GRUPOS, []) if s[GRUPO_TIPO].lower() != GRUPO_PRIVADO]
                    
                    # Guardar grupos privados para mostrarlas al final
                    grupos_privados.extend([s for s in asignatura.get(GRUPOS, []) if s[GRUPO_TIPO].lower() == GRUPO_PRIVADO])
                    
                    # Mostrar grupos de esta asignatura
                    if grupos_asignatura:
                        for grupo in grupos_asignatura:
                            proposito = grupo.get(GRUPO_PROPOSITO, '').lower() if grupo.get(GRUPO_PROPOSITO) else GENERAL
                            nombre_grupo = grupo.get(GRUPO_NOMBRE, 'grupo sin nombre')
                            
                            # Seleccionar emoji según el propósito
                            emoji = "📢" if proposito == GRUPO_PROPOSITO_AVISOS else "👥" if proposito == GRUPO_PROPOSITO_GRUPAL else "🔵"
                            
                            # Mostrar como hipervínculo si tiene enlace
                            if grupo.get(GRUPO_ENLACE):
                                mensaje += f"  {emoji} [{nombre_grupo}]({grupo[GRUPO_ENLACE]})\n"
                            else:
                                mensaje += f"  {emoji} {nombre_grupo} (sin enlace disponible)\n"
                    else:
                        mensaje += f"  ℹ️ No hay grupos disponibles para esta asignatura\n"
                    
                    mensaje += "\n"  # Espacio entre asignaturas
    
            # Mostrar grupos de la categoría "general" si existen
            grupos_generales = prof_info[MATRICULAS].get(GENERAL, {}).get(GRUPOS, [])
            grupos_generales_no_privados = [s for s in grupos_generales if s[GRUPO_TIPO].lower() != GRUPO_PRIVADO]
            
            # Añadir grupos privados de la categoría general
            grupos_privados.extend([s for s in grupos_generales if s[GRUPO_TIPO].lower() == GRUPO_PRIVADO])
            
            # Mostrar grupos generales si existen
            if grupos_generales_no_privados:
                mensaje += "🌐 *grupos Generales:*\n"
                for grupo in grupos_generales_no_privados:
                    proposito = grupo.get(GRUPO_PROPOSITO, '').lower() if grupo.get(GRUPO_PROPOSITO) else GENERAL
                    nombre_grupo = grupo.get(GRUPO_NOMBRE, 'grupo sin nombre')
                    
                    # Seleccionar emoji según el propósito
                    emoji = "📢" if proposito == GRUPO_PROPOSITO_AVISOS else "👥" if proposito == GRUPO_PROPOSITO_GRUPAL else "🔵"
                    
                    # Mostrar como hipervínculo si tiene enlace
                    if grupo.get(GRUPO_ENLACE):
                        mensaje += f"  {emoji} [{nombre_grupo}]({grupo[GRUPO_ENLACE]})\n"
                    else:
                        mensaje += f"  {emoji} {nombre_grupo} (sin enlace disponible)\n"
                
                mensaje += "\n"  # Espacio después de grupos generales
            
            # Mostrar grupos privados separadamente (de todas las asignaturas) si existen
            if grupos_privados:
                primera_privado = grupos_privados[0]
                mensaje += f"🔐 *Tutoría Privado*\n"
                
                # Enviar mensaje primero para que aparezca el texto
                bot.send_message(
                    chat_id,
                    mensaje,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
                mensaje = ""  # Reiniciar mensaje
                
                # Enviar botón en mensaje separado
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(
                    "🔒 Solicitar acceso a tutoría privado", 
                    callback_data=f"{SOLICITAR_GRUPO}{primera_privado[GRUPO_ID]}_{profesor_id}"
                ))
                
                bot.send_message(
                    chat_id,
                    "Haz clic en el botón para solicitar acceso:",
                    reply_markup=markup
                )
            else:
                # Enviar mensaje solo si hay contenido y no hay grupos privados
                if mensaje.strip():
                    bot.send_message(
                        chat_id,
                        mensaje,
                        parse_mode="Markdown",
                        disable_web_page_preview=True
                    )
            
    # Aquí añadimos el resto de handlers para tutorias
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith(SOLICITAR_GRUPO))
    def handle_solicitar_grupo(call):
        """Gestiona solicitudes de acceso a grupos de tutoría privado"""
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        
        print(f"\n### INICIO SOLICITAR_grupo ###")
        print(f"Chat ID: {chat_id}, User ID: {user_id}")
        print(f"Callback data: {call.data}")
        
        try:
            # Extraer IDs de la grupo y profesor del callback_data
            # Modificar esta línea para manejar el formato correcto del callback_data
            parts = call.data.split("_")
            grupo_id = int(parts[2])
            profesor_id = int(parts[3])
            
            # 1. Verificar que el usuario solicitante es un estudiante registrado
            user = get_usuarios(USUARIO_ID_TELEGRAM=user_id)[0]
            if not user:
                bot.answer_callback_query(call.id, "❌ No estás registrado en el sistema.")
                return
                
            if user[USUARIO_TIPO] != USUARIO_TIPO_ESTUDIANTE:
                bot.answer_callback_query(call.id, "⚠️ Solo los estudiantes pueden solicitar tutorías privados.")
                return
            
            # 2. Obtener información de la grupo y del profesor            
            grupo = get_grupos_tutoria(GRUPO_ID=grupo_id)[0]
            profesor = get_usuarios(USUARIO_ID=profesor_id)[0]
            
            if not grupo:
                bot.answer_callback_query(call.id, "❌ No se encontró la grupo solicitada.")
                return
                
            # 3. Verificar si estamos en horario de tutoría del profesor
            print(f"Verificando horario de tutoría para profesor_id={profesor_id}")
            print(f"Horario del profesor: {profesor[USUARIO_HORARIO]}")
            
            es_horario_tutoria = verificar_horario_tutoria(profesor[USUARIO_HORARIO])
            print(f"¿Está en horario de tutoría? {es_horario_tutoria}")
            
            if not es_horario_tutoria:
                # No estamos en horario de tutoría
                bot.answer_callback_query(call.id, "⏰ No es horario de tutoría del profesor.")

                texto = (f"⏰ *No es horario de tutoría*\n\n"
                        f"El profesor {profesor[USUARIO_NOMBRE]} {profesor[USUARIO_APELLIDOS] or ''} "
                        f"tiene el siguiente horario de tutorías:")

                dias = profesor[USUARIO_HORARIO].split(', ')
            
                dia_anterior = ""
                for dia in dias:
                    dia = dia.split(' ')
                    if dia[0] != dia_anterior:
                        texto += f"\n  -{dia[0]} {dia[1]}"
                    else:
                        texto += f", {dia[1]}"
                    dia_anterior = dia[0]
                
                texto += f"\n\nPor favor, intenta solicitar acceso durante estos horarios."

                # Informar al estudiante con más detalle
                bot.send_message(
                    chat_id,
                    texto,
                    parse_mode="Markdown"
                )
                return
            
            # 4. Estamos en horario de tutoría, enviar notificación al profesor
            # Obtener datos del estudiante para la notificación
            estudiante_nombre = f"{user[USUARIO_NOMBRE]} {user[USUARIO_APELLIDOS] or ''}".strip()
            
            # Crear mensaje de notificación para el profesor
            mensaje_profesor = (
                f"🔔 *Solicitud de tutoría privado*\n\n"
                f"👤 Estudiante: {estudiante_nombre}\n"
                f"📧 Email: {user[USUARIO_EMAIL] or 'No disponible'}\n"
            )
            
            if grupo['Asignatura']:
                mensaje_profesor += f"📚 Asignatura: {grupo[GRUPO_ASIGNATURA]}\n"
            
            mensaje_profesor += (
                f"\nEl estudiante ha solicitado acceso a tu grupo de tutorías privados."
            )
            
            # Crear botones para que el profesor pueda aprobar o rechazar
            markup_profesor = types.InlineKeyboardMarkup(row_width=2)
            markup_profesor.add(
                types.InlineKeyboardButton("✅ Aprobar", callback_data=f"{APROBAR_TUTORIA}{grupo_id}_{user[USUARIO_ID]}"),
                types.InlineKeyboardButton("❌ Rechazar", callback_data=f"{RECHAZAR_TUTORIA}{grupo_id}_{user[USUARIO_ID]}")
            )
            
            # 5. Generar mensaje de confirmación para el estudiante (sin enviar enlace todavía)
            if grupo[GRUPO_ENLACE]:
                # Mensaje para el estudiante (solo confirmación de solicitud)
                mensaje_estudiante = (
                    f"✅ *Solicitud de tutoría enviada*\n\n"
                    f"Tu solicitud ha sido enviada al profesor "
                    f"{profesor[USUARIO_NOMBRE]} {profesor[USUARIO_APELLIDOS] or ''}.\n\n"
                    f"Recibirás una notificación cuando el profesor responda a tu solicitud."
                )
                
                # Enviar mensaje de confirmación al estudiante
                bot.send_message(
                    chat_id,
                    mensaje_estudiante,
                    parse_mode="Markdown"
                )
            else:
                # Informar que no hay enlace disponible
                bot.send_message(
                    chat_id,
                    "⚠️ Esta grupo no tiene un enlace de invitación configurado. "
                    "El profesor deberá proporcionarte el acceso manualmente si aprueba tu solicitud.",
                    parse_mode="Markdown"
                )
            
            # 6. Enviar la notificación al profesor
            if profesor[USUARIO_ID_TELEGRAM]:
                bot.send_message(
                    profesor[USUARIO_ID_TELEGRAM],
                    mensaje_profesor,
                    parse_mode="Markdown",
                    reply_markup=markup_profesor
                )
            else:
                # El profesor no tiene Telegram registrado
                bot.send_message(
                    chat_id,
                    "⚠️ El profesor no tiene cuenta de Telegram registrada. "
                    "Se enviará tu solicitud por correo electrónico.",
                    parse_mode="Markdown"
                )
                
            # Confirmar al usuario que se procesó la solicitud
            bot.answer_callback_query(call.id, "✅ Solicitud enviada correctamente")
            
        except Exception as e:
            logger.error(f"Error al procesar solicitud de grupo: {e}")
            bot.answer_callback_query(call.id, "❌ Ha ocurrido un error al procesar tu solicitud.")
            bot.send_message(chat_id, "Lo sentimos, ha ocurrido un error al procesar tu solicitud de tutoría.")
        
        print("### FIN SOLICITAR_grupo ###\n")

    @bot.callback_query_handler(func=lambda call: call.data.startswith(APROBAR_TUTORIA))
    def handle_aprobar_tutoria(call):
        """Maneja la aprobación de una solicitud de tutoría privado"""
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        
        print(f"\n### INICIO APROBAR_TUTORIA ###")
        print(f"Chat ID: {chat_id}, User ID: {user_id}")
        print(f"Callback data: {call.data}")
        
        try:
            # Extraer los IDs necesarios del callback_data
            parts = call.data.split("_")
            if len(parts) < 4:
                bot.answer_callback_query(call.id, "❌ Formato de solicitud incorrecto.")
                return
                
            grupo_id = int(parts[2])
            estudiante_id = int(parts[3])
            
            # 1. Verificar que el usuario que aprueba es el profesor propietario de la grupo
            profesor = get_usuarios(USUARIO_ID_TELEGRAM=user_id)[0]
            if not profesor or profesor[USUARIO_TIPO] != USUARIO_TIPO_PROFESOR:
                bot.answer_callback_query(call.id, "⚠️ Solo el profesor propietario puede aprobar solicitudes.")
                return
            
            # 2. Obtener información de la grupo y del estudiante       
            # Verificar que la grupo pertenece al profesor
            grupo = get_grupos_tutoria(GRUPO_ID=grupo_id, GRUPO_ID_USUARIO=profesor[USUARIO_ID])[0]
            
            if not grupo:
                bot.answer_callback_query(call.id, "❌ No tienes permisos para esta grupo o no existe.")
                return
            
            # 3. Obtener información del estudiante
            estudiante = get_usuarios(USUARIO_ID=estudiante_id, USUARIO_TIPO=USUARIO_TIPO_ESTUDIANTE)
            if not estudiante:
                bot.answer_callback_query(call.id, "❌ No se encontró al estudiante.")
                return
            estudiante = estudiante[0]
        
            
            # 5. Enviar enlace de invitación al estudiante
            if grupo[GRUPO_ENLACE] and estudiante[USUARIO_ID_TELEGRAM]:
                mensaje_estudiante = (
                    f"✅ *Tu solicitud de tutoría ha sido aprobada*\n\n"
                    f"El profesor {profesor[USUARIO_NOMBRE]} {profesor[USUARIO_APELLIDOS] or ''} "
                    f"ha aprobado tu solicitud de acceso a la grupo de tutorías.\n\n"
                    f"Usa este enlace para unirte al grupo: {grupo[GRUPO_ENLACE]}"
                )
                
                bot.send_message(
                    estudiante[USUARIO_ID_TELEGRAM],
                    mensaje_estudiante,
                    parse_mode="Markdown"
                )
                print(f"✅ Enlace de invitación enviado al estudiante {estudiante[USUARIO_ID]}")
            else:
                # Si no hay enlace o ID de Telegram
                bot.send_message(
                    chat_id,
                    f"⚠️ No se pudo enviar el enlace de invitación a {estudiante[USUARIO_NOMBRE]} {estudiante[USUARIO_APELLIDOS] or ''}.\n"
                    f"Verifique que la grupo tenga un enlace de invitación configurado."
                )
        
            # 6. Actualizar el mensaje de solicitud para mostrar que fue aprobada
            nombre_completo = f"{estudiante[USUARIO_NOMBRE]} {estudiante[USUARIO_APELLIDOS] or ''}".strip()
            
            mensaje_actualizado = (
                f"✅ *Solicitud APROBADA*\n\n"
                f"👤 Estudiante: {nombre_completo}\n"
                f"📧 Email: {estudiante[USUARIO_EMAIL] or 'No disponible'}\n\n"
                f"Acceso concedido a la grupo: {grupo[GRUPO_NOMBRE]}"
            )
            
            # Eliminar los botones de aprobar/rechazar
            bot.edit_message_text(
                mensaje_actualizado,
                chat_id=chat_id,
                message_id=call.message.message_id,
                parse_mode="Markdown"
            )
            
            bot.answer_callback_query(call.id, "✅ Solicitud aprobada con éxito")
            
            print(f"✅ Solicitud de tutoría aprobada: Estudiante {estudiante_id} añadido a grupo {grupo_id}")
            
        except Exception as e:
            print(f"❌ Error al aprobar solicitud: {e}")
            import traceback
            traceback.print_exc()
            bot.answer_callback_query(call.id, "❌ Ha ocurrido un error al procesar la aprobación")
    
        print("### FIN APROBAR_TUTORIA ###\n")

    @bot.callback_query_handler(func=lambda call: call.data.startswith(RECHAZAR_TUTORIA))
    def handle_rechazar_tutoria(call):
        """Maneja el rechazo de una solicitud de tutoría privado"""
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        
        print(f"\n### INICIO RECHAZAR_TUTORIA ###")
        print(f"Chat ID: {chat_id}, User ID: {user_id}")
        print(f"Callback data: {call.data}")
        
        try:
            # Extraer los IDs necesarios del callback_data
            # Formato: rechazar_tutoria_grupo_estudiante
            parts = call.data.split("_")
            if len(parts) < 4:
                bot.answer_callback_query(call.id, "❌ Formato de solicitud incorrecto.")
                return
                
            grupo_id = int(parts[2])
            estudiante_id = int(parts[3])
            
            # Verificar que el usuario que rechaza es el profesor propietario de la grupo
            profesor = get_usuarios(USUARIO_ID_TELEGRAM=user_id)[0]
            if not profesor or profesor[USUARIO_TIPO] != USUARIO_TIPO_PROFESOR:
                bot.answer_callback_query(call.id, "⚠️ Solo el profesor propietario puede rechazar solicitudes.")
                return
            
            # Obtener información del estudiante y la grupo            
            estudiante = get_usuarios(USUARIO_ID=estudiante_id)[0]
            
            grupo = get_grupos_tutoria(GRUPO_ID=grupo_id)[0]
            
            
            if not estudiante or not grupo:
                bot.answer_callback_query(call.id, "❌ Datos de solicitud no encontrados.")
                return
            
            # Actualizar el mensaje para mostrar que fue rechazada
            nombre_completo = f"{estudiante[USUARIO_NOMBRE]} {estudiante[USUARIO_APELLIDOS] or ''}".strip()
            
            mensaje_actualizado = (
                f"❌ *Solicitud RECHAZADA*\n\n"
                f"👤 Estudiante: {nombre_completo}\n"
                f"📧 Email: {estudiante[USUARIO_EMAIL] or 'No disponible'}\n\n"
                f"Acceso denegado a la grupo: {grupo[GRUPO_NOMBRE]}"
            )
            
            # Eliminar los botones de aprobar/rechazar
            bot.edit_message_text(
                mensaje_actualizado,
                chat_id=chat_id,
                message_id=call.message.message_id,
                parse_mode="Markdown"
            )
            
            # Notificar al estudiante si tiene Telegram registrado
            if estudiante[USUARIO_ID_TELEGRAM]:
                mensaje_rechazo = (
                    f"❌ *Tu solicitud de tutoría ha sido rechazada*\n\n"
                    f"El profesor {profesor[USUARIO_NOMBRE]} {profesor[USUARIO_APELLIDOS] or ''} "
                    f"ha rechazado tu solicitud de acceso a la grupo de tutorías.\n\n"
                    f"Si necesitas más información, contacta directamente con el profesor."
                )
                
                bot.send_message(
                    estudiante[USUARIO_ID_TELEGRAM],
                    mensaje_rechazo,
                    parse_mode="Markdown"
                )
            
            bot.answer_callback_query(call.id, "✅ Solicitud rechazada")
            
        except Exception as e:
            print(f"❌ Error al rechazar solicitud: {e}")
            import traceback
            traceback.print_exc()
            bot.answer_callback_query(call.id, "❌ Ha ocurrido un error al procesar el rechazo")
    
        print("### FIN RECHAZAR_TUTORIA ###\n")
# Funciones auxiliares para el manejo de solicitudes de tutoría

def verificar_horario_tutoria(horario_str):
    """
    Verifica si estamos en horario de tutoría del profesor
    
    Args:
        horario_str: cadena con formatos como:
        - "Lunes de 10:00 a 12:00"
        - "Miércoles 09:00-12:00"
        
    Returns:
        bool: True si la hora actual está dentro del horario de tutorías
    """
    import re
    from datetime import datetime, time
    
    # Si no hay horario definido, no se puede verificar
    if not horario_str or horario_str.strip() == '':
        print("No hay horario definido")
        return False
        
    # Obtener día y hora actual
    ahora = datetime.now()
    
    # Nombres de días en español e inglés para hacer la verificación más robusta
    dias_semana = {
        0: ['lunes', 'monday'],
        1: ['martes', 'tuesday'],
        2: ['miércoles', 'miercoles', 'wednesday'],
        3: ['jueves', 'thursday'],
        4: ['viernes', 'friday'],
        5: ['sábado', 'sabado', 'saturday'],
        6: ['domingo', 'sunday']
    }
    
    # Obtener día actual (0=lunes, 1=martes, etc.)
    dia_semana_actual = ahora.weekday()
    nombres_dia_actual = dias_semana[dia_semana_actual]
    
    # Crear objeto time para comparar horas
    hora_actual = time(ahora.hour, ahora.minute)
    
    # Convertir todo a minúsculas para comparación insensible a mayúsculas
    horario_lower = horario_str.lower()
    
    # Debug: Mostrar información para diagnóstico
    print(f"Verificando horario: {horario_str}")
    print(f"Día actual: {ahora.strftime('%A')} ({dia_semana_actual})")
    print(f"Hora actual: {hora_actual}")
    print(f"Nombres para el día actual: {nombres_dia_actual}")
    
    # Buscar patrones de horario:
    # 1. Formato "Lunes de 10:00 a 12:00"
    patron1 = r'(lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\s+de\s+(\d{1,2}):?(\d{2})?\s+a\s+(\d{1,2}):?(\d{2})?'
    
    # 2. Formato "Miércoles 09:00-12:00"
    patron2 = r'(lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\s+(\d{1,2}):?(\d{2})?-(\d{1,2}):?(\d{2})?'
    
    # Flag para indicar si encontramos algún horario que coincida
    encontrado = False
    
    # Comprobar el primer formato (Día de HH:MM a HH:MM)
    for match in re.finditer(patron1, horario_lower):
        dia_horario = match.group(1)
        
        # Comprobar si el día coincide con el actual
        es_hoy = any(dia_nombre in dia_horario for dia_nombre in nombres_dia_actual)
        
        if not es_hoy:
            continue
            
        # Extraer hora inicio y fin
        hora_inicio = int(match.group(2))
        minuto_inicio = int(match.group(3) or 0)
        hora_fin = int(match.group(4))
        minuto_fin = int(match.group(5) or 0)
        
        # Crear objetos time para comparar
        tiempo_inicio = time(hora_inicio, minuto_inicio)
        tiempo_fin = time(hora_fin, minuto_fin)
        
        # Debug: Mostrar cada horario encontrado para diagnóstico
        print(f"Formato 1 - Horario encontrado: {dia_horario} de {tiempo_inicio} a {tiempo_fin}")
        encontrado = True
        
        # Verificar si la hora actual está en el rango
        if tiempo_inicio <= hora_actual <= tiempo_fin:
            print(f"✅ Dentro de horario: {tiempo_inicio} <= {hora_actual} <= {tiempo_fin}")
            return True
        else:
            print(f"❌ Fuera de horario: {hora_actual} no está entre {tiempo_inicio} y {tiempo_fin}")
    
    # Comprobar el segundo formato (Día HH:MM-HH:MM)
    for match in re.finditer(patron2, horario_lower):
        dia_horario = match.group(1)
        
        # Comprobar si el día coincide con el actual
        es_hoy = any(dia_nombre in dia_horario for dia_nombre in nombres_dia_actual)
        
        if not es_hoy:
            continue
            
        # Extraer hora inicio y fin
        hora_inicio = int(match.group(2))
        minuto_inicio = int(match.group(3) or 0)
        hora_fin = int(match.group(4))
        minuto_fin = int(match.group(5) or 0)
        
        # Crear objetos time para comparar
        tiempo_inicio = time(hora_inicio, minuto_inicio)
        tiempo_fin = time(hora_fin, minuto_fin)
        
        # Debug: Mostrar cada horario encontrado para diagnóstico
        print(f"Formato 2 - Horario encontrado: {dia_horario} {tiempo_inicio}-{tiempo_fin}")
        encontrado = True
        
        # Verificar si la hora actual está en el rango
        if tiempo_inicio <= hora_actual <= tiempo_fin:
            print(f"✅ Dentro de horario: {tiempo_inicio} <= {hora_actual} <= {tiempo_fin}")
            return True
        else:
            print(f"❌ Fuera de horario: {hora_actual} no está entre {tiempo_inicio} y {tiempo_fin}")
    
    # Si no se encontró ninguna coincidencia para el día actual, informarlo
    if not encontrado:
        print(f"No se encontraron horarios para el día actual ({ahora.strftime('%A')})")
    
    return False