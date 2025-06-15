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
    get_user_by_telegram_id,
    get_carreras_by_area,
    get_matriculas_by_user,
    get_db_connection,
    get_matriculas_usuario,
    get_profesores_asignatura,
    get_salas_profesor_asignatura
)

# Añadir la función directamente en este archivo
def escape_markdown(text: str) -> str:
    """Escapa caracteres especiales de Markdown para evitar errores de formato"""
    if not text:
        return ""
        
    # Caracteres que necesitan escape en Markdown
    markdown_chars = ['_', '*', '`', '[', ']', '(', ')', '#', '+', '-', '.', '!']
    
    # Reemplazar cada caracter especial con su versión escapada
    result = text
    for char in markdown_chars:
        result = result.replace(char, '\\' + char)
        
    return result






# Referencias externas necesarias
user_states = {}
user_data = {}
estados_timestamp = {}  

def register_handlers(bot):
    """Registra todos los handlers de tutorías"""
    
    @bot.message_handler(commands=['tutoria'])
    def handle_tutoria_command(message):
        """Muestra profesores y salas disponibles para las asignaturas del estudiante"""
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        print(f"\n### INICIO COMANDO TUTORIA ###")
        print(f"Usuario ID: {user_id}, Chat ID: {chat_id}")
        
        # Obtener información del usuario
        user = get_user_by_telegram_id(user_id)
        
        # Diagnóstico: Verificar si hay salas en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Contar todas las salas
        cursor.execute("SELECT COUNT(*) as total FROM Grupos_tutoria")
        total_salas = cursor.fetchone()['total']
        print(f"Total de salas en la BD: {total_salas}")
        
        # Mostrar detalles de algunas salas para diagnóstico
        if total_salas > 0:
            cursor.execute("""
                SELECT 
                    g.id_sala, g.Id_usuario, g.Nombre_sala, g.Proposito_sala, 
                    g.Tipo_sala, g.Id_asignatura, a.Nombre as NombreAsignatura
                FROM Grupos_tutoria g
                LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
                LIMIT 5
            """)
            
            print("Primeras 5 salas en la BD:")
            for sala in cursor.fetchall():
                print(f"  - ID: {sala['id_sala']}, Nombre: {sala['Nombre_sala']}")
                print(f"    Profesor: {sala['Id_usuario']}, Asignatura: {sala['Id_asignatura']} ({sala['NombreAsignatura']})")
                print(f"    Tipo: {sala['Tipo_sala']}, Propósito: {sala['Proposito_sala']}")
                print("    ---")
        
        if not user:
            bot.send_message(chat_id, "❌ No estás registrado. Usa /start para registrarte.")
            print("❌ Usuario no registrado")
            return
        
        if user['Tipo'] != 'estudiante':
            bot.send_message(chat_id, "⚠️ Esta funcionalidad está disponible solo para estudiantes.")
            print("⚠️ Usuario no es estudiante")
            return
        
        print(f"✅ Estudiante: {user['Nombre']} {user['Apellidos'] or ''}")
        
        # Obtener las asignaturas del estudiante
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT a.Id_asignatura, a.Nombre as Asignatura
            FROM Matriculas m
            JOIN Asignaturas a ON m.Id_asignatura = a.Id_asignatura
            WHERE m.Id_usuario = ?
        """, (user['Id_usuario'],))
        
        asignaturas = cursor.fetchall()
        
        if not asignaturas:
            bot.send_message(chat_id, "❌ No estás matriculado en ninguna asignatura.")
            conn.close()
            print("❌ Estudiante sin asignaturas")
            return
        
        print(f"✅ Asignaturas encontradas: {len(asignaturas)}")
        
        # Obtener IDs de asignaturas para usar en consultas
        asignaturas_ids = [a['Id_asignatura'] for a in asignaturas]
        placeholders = ','.join(['?'] * len(asignaturas_ids))
        
        # Obtener profesores que tienen grupos de tutoría para estas asignaturas
        # O profesores que son de estas asignaturas según las matrículas (donde son docentes)
        cursor.execute(f"""
            SELECT DISTINCT 
                u.Id_usuario, 
                u.Nombre, 
                u.Apellidos, 
                u.Email_UGR, 
                u.horario
            FROM Usuarios u
            WHERE u.Tipo = 'profesor' 
            AND (
                -- Profesores que han creado grupos para estas asignaturas
                u.Id_usuario IN (
                    SELECT DISTINCT g.Id_usuario 
                    FROM Grupos_tutoria g 
                    WHERE g.Id_asignatura IN ({placeholders})
                )
                OR
                -- O profesores que tienen matrículas como docentes en estas asignaturas
                u.Id_usuario IN (
                    SELECT DISTINCT m.Id_usuario 
                    FROM Matriculas m 
                    WHERE m.Id_asignatura IN ({placeholders}) AND m.Tipo = 'docente'
                )
            )
            ORDER BY u.Apellidos, u.Nombre
        """, asignaturas_ids + asignaturas_ids)
        
        profesores_raw = cursor.fetchall()
        print(f"✅ Profesores encontrados: {len(profesores_raw)}")
        
        # Convertir a diccionario para facilitar el acceso
        profesores = {}
        for profesor in profesores_raw:
            prof_id = profesor['Id_usuario']
            profesores[prof_id] = {
                'id': prof_id,
                'nombre': f"{profesor['Nombre']} {profesor['Apellidos'] or ''}".strip(),
                'email': profesor['Email_UGR'],
                'horario': profesor['horario'] or 'No especificado',
                'asignaturas': {}
            }
        
        # Obtener asignaturas por profesor (basado en matrículas de tipo 'docente' y en grupos creados)
        for profesor_id in profesores:
            # Buscar asignaturas por matrículas donde es docente
            cursor.execute(f"""
                SELECT DISTINCT
                    a.Id_asignatura,
                    a.Nombre as NombreAsignatura,
                    a.Codigo_Asignatura as Codigo
                FROM Matriculas m
                JOIN Asignaturas a ON m.Id_asignatura = a.Id_asignatura
                WHERE m.Id_usuario = ? AND m.Tipo = 'docente' AND m.Id_asignatura IN ({placeholders})
                
                UNION
                
                -- Asignaturas por grupos que ha creado
                SELECT DISTINCT
                    a.Id_asignatura,
                    a.Nombre as NombreAsignatura,
                    a.Codigo_Asignatura as Codigo
                FROM Grupos_tutoria g
                JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
                WHERE g.Id_usuario = ? AND g.Id_asignatura IN ({placeholders})
            """, [profesor_id] + asignaturas_ids + [profesor_id] + asignaturas_ids)
            
            asignaturas_profesor = cursor.fetchall()
            
            for asig in asignaturas_profesor:
                if asig['Id_asignatura'] is not None:  # Si la asignatura existe
                    profesores[profesor_id]['asignaturas'][asig['Id_asignatura']] = {
                        'id': asig['Id_asignatura'],
                        'nombre': asig['NombreAsignatura'],
                        'codigo': asig['Codigo'],
                        'salas': []

                    }
        
        # Inicializar la categoría general para cada profesor
        for profesor_id in profesores:
            profesores[profesor_id]['asignaturas']['general'] = {
                'id': 'general',
                'nombre': 'General',
                'salas': []
            }
        
        # Obtener todas las salas de cada profesor
        for profesor_id in profesores:
            cursor.execute("""
                SELECT 
                    g.id_sala,
                    g.Nombre_sala,
                    g.Proposito_sala,
                    g.Chat_id,
                    g.Tipo_sala,
                    g.Id_asignatura,
                    g.Enlace_invitacion,
                    a.Nombre as NombreAsignatura
                FROM Grupos_tutoria g
                LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
                WHERE g.Id_usuario = ?
            """, (profesor_id,))
            
            salas = cursor.fetchall()
            print(f"Encontradas {len(salas)} salas para el profesor {profesor_id}")
            
            # Clasificar las salas por asignatura
            for sala in salas:
                sala_data = {
                    'id': sala['id_sala'],
                    'nombre': sala['Nombre_sala'],
                    'proposito': sala['Proposito_sala'],
                    'tipo': sala['Tipo_sala'],
                    'enlace': sala['Enlace_invitacion'],
                    'chat_id': sala['Chat_id'],
                    'asignatura': sala['NombreAsignatura']
                }
                
                # Asignar la sala a su asignatura correspondiente (o a general si no tiene)
                if sala['Id_asignatura'] is not None:
                    asignatura_id = sala['Id_asignatura']
                    # Verificar que la asignatura existe en el diccionario del profesor
                    if asignatura_id in profesores[profesor_id]['asignaturas']:
                        profesores[profesor_id]['asignaturas'][asignatura_id]['salas'].append(sala_data)
                        print(f"Asignada sala '{sala['Nombre_sala']}' a asignatura ID {asignatura_id}")
                    else:
                        # Si por alguna razón la asignatura no está en el diccionario, asignar a general
                        profesores[profesor_id]['asignaturas']['general']['salas'].append(sala_data)
                        print(f"Sala '{sala['Nombre_sala']}' asignada a 'general' (asignatura ID {asignatura_id} no encontrada)")
                else:
                    # Si la sala no tiene asignatura, agregarla a la categoría "general"
                    profesores[profesor_id]['asignaturas']['general']['salas'].append(sala_data)
                    print(f"Sala '{sala['Nombre_sala']}' asignada a 'general' (sin asignatura asociada)")

        conn.close()
        
        # Si no se encontró ningún profesor, mostrar mensaje y terminar
        if not profesores:
            bot.send_message(chat_id, "❌ No se encontraron profesores para tus asignaturas.")
            return
        
        # Mejorar la parte que genera el mensaje y muestra las salas
        for profesor_id, prof_info in profesores.items():
            # Sección del profesor
            mensaje = f"👨‍🏫 *Profesor: {escape_markdown(prof_info['nombre'])}*\n"
            mensaje += f"📧 Email: {escape_markdown(prof_info['email'])}\n"
            mensaje += f"🕗 Horario: {escape_markdown(prof_info['horario'])}\n\n"
            
            markup = types.InlineKeyboardMarkup()  # Crear markup para botones
            
            # Recopilar todas las salas del profesor desde todas las asignaturas
            todas_las_salas = []
            for asignatura_id, asignatura in prof_info['asignaturas'].items():
                if 'salas' in asignatura:
                    for sala in asignatura['salas']:
                        sala['asignatura_id'] = asignatura_id
                        sala['asignatura_nombre'] = asignatura['nombre']
                        todas_las_salas.append(sala)
            
            print(f"Total salas para profesor {profesor_id}: {len(todas_las_salas)}")
            
            # Primero mostrar las asignaturas que imparte
            mensaje += "📚 *Asignaturas:*\n"
            
            # Variable para controlar si hay salas privadas
            salas_privadas = []
            
            for asignatura_id, asignatura in prof_info['asignaturas'].items():
                if asignatura_id != 'general':  # Solo las asignaturas regulares, no la categoría "general"
                    nombre = escape_markdown(asignatura['nombre'])
                    codigo = asignatura.get('codigo', '') or ''
                    
                    # Mostrar información de la asignatura
                    mensaje += f"• {nombre}"
                    if codigo:
                        mensaje += f" ({codigo})"
                    mensaje += "\n"
                    
                    # Filtrar salas para esta asignatura específica
                    salas_asignatura = [s for s in asignatura.get('salas', []) if s['tipo'].lower() != 'privada']
                    
                    # Guardar salas privadas para mostrarlas al final
                    salas_privadas.extend([s for s in asignatura.get('salas', []) if s['tipo'].lower() == 'privada'])
                    
                    # Mostrar salas de esta asignatura
                    if salas_asignatura:
                        for sala in salas_asignatura:
                            proposito = sala.get('proposito', '').lower() if sala.get('proposito') else 'general'
                            nombre_sala = escape_markdown(sala.get('nombre', 'Sala sin nombre'))
                            
                            # Seleccionar emoji según el propósito
                            emoji = "📢" if proposito == 'avisos' else "👥" if proposito == 'grupal' else "🔵"
                            
                            # Mostrar como hipervínculo si tiene enlace
                            if sala.get('enlace'):
                                mensaje += f"  {emoji} [{nombre_sala}]({sala['enlace']})\n"
                            else:
                                mensaje += f"  {emoji} {nombre_sala} (sin enlace disponible)\n"
                    else:
                        mensaje += f"  ℹ️ No hay salas disponibles para esta asignatura\n"
                    
                    mensaje += "\n"  # Espacio entre asignaturas
    
            # Mostrar salas de la categoría "general" si existen
            salas_generales = prof_info['asignaturas'].get('general', {}).get('salas', [])
            salas_generales_no_privadas = [s for s in salas_generales if s['tipo'].lower() != 'privada']
            
            # Añadir salas privadas de la categoría general
            salas_privadas.extend([s for s in salas_generales if s['tipo'].lower() == 'privada'])
            
            # Mostrar salas generales si existen
            if salas_generales_no_privadas:
                mensaje += "🌐 *Salas Generales:*\n"
                for sala in salas_generales_no_privadas:
                    proposito = sala.get('proposito', '').lower() if sala.get('proposito') else 'general'
                    nombre_sala = escape_markdown(sala.get('nombre', 'Sala sin nombre'))
                    
                    # Seleccionar emoji según el propósito
                    emoji = "📢" if proposito == 'avisos' else "👥" if proposito == 'grupal' else "🔵"
                    
                    # Mostrar como hipervínculo si tiene enlace
                    if sala.get('enlace'):
                        mensaje += f"  {emoji} [{nombre_sala}]({sala['enlace']})\n"
                    else:
                        mensaje += f"  {emoji} {nombre_sala} (sin enlace disponible)\n"
                
                mensaje += "\n"  # Espacio después de salas generales
            
            # Mostrar salas privadas separadamente (de todas las asignaturas) si existen
            if salas_privadas:
                primera_privada = salas_privadas[0]
                mensaje += f"🔐 *Tutoría Privada*\n"
                
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
                    "🔒 Solicitar acceso a tutoría privada", 
                    callback_data=f"solicitar_sala_{primera_privada['id']}_{profesor_id}"
                ))
                
                bot.send_message(
                    chat_id,
                    "Haz clic en el botón para solicitar acceso:",
                    reply_markup=markup
                )
            else:
                # Enviar mensaje solo si hay contenido y no hay salas privadas
                if mensaje.strip():
                    bot.send_message(
                        chat_id,
                        mensaje,
                        parse_mode="Markdown",
                        disable_web_page_preview=True
                    )
            
    # Aquí añadimos el resto de handlers para tutorias
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith("solicitar_sala_"))
    def handle_solicitar_sala(call):
        """Gestiona solicitudes de acceso a salas de tutoría privada"""
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        
        print(f"\n### INICIO SOLICITAR_SALA ###")
        print(f"Chat ID: {chat_id}, User ID: {user_id}")
        print(f"Callback data: {call.data}")
        
        try:
            # Extraer IDs de la sala y profesor del callback_data
            # Modificar esta línea para manejar el formato correcto del callback_data
            parts = call.data.split("_")
            sala_id = int(parts[2])
            profesor_id = int(parts[3])
            
            # 1. Verificar que el usuario solicitante es un estudiante registrado
            user = get_user_by_telegram_id(user_id)
            if not user:
                bot.answer_callback_query(call.id, "❌ No estás registrado en el sistema.")
                return
                
            if user['Tipo'] != 'estudiante':
                bot.answer_callback_query(call.id, "⚠️ Solo los estudiantes pueden solicitar tutorías privadas.")
                return
            
            # 2. Obtener información de la sala y del profesor
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    g.*,
                    u.Nombre as NombreProfesor,
                    u.Apellidos as ApellidosProfesor,
                    u.TelegramID as ProfesorTelegramID,
                    u.Horario as HorarioProfesor,
                    a.Nombre as NombreAsignatura
                FROM Grupos_tutoria g
                JOIN Usuarios u ON g.Id_usuario = u.Id_usuario
                LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
                WHERE g.id_sala = ? AND g.Id_usuario = ?
            """, (sala_id, profesor_id))
            
            sala = cursor.fetchone()
            conn.close()
            
            if not sala:
                bot.answer_callback_query(call.id, "❌ No se encontró la sala solicitada.")
                return
                
            # 3. Verificar si estamos en horario de tutoría del profesor
            print(f"Verificando horario de tutoría para profesor_id={profesor_id}")
            print(f"Horario del profesor: {sala['HorarioProfesor']}")
            
            es_horario_tutoria = verificar_horario_tutoria(sala['HorarioProfesor'])
            print(f"¿Está en horario de tutoría? {es_horario_tutoria}")
            
            if not es_horario_tutoria:
                # No estamos en horario de tutoría
                bot.answer_callback_query(call.id, "⏰ No es horario de tutoría del profesor.")
                
                # Informar al estudiante con más detalle
                bot.send_message(
                    chat_id,
                    f"⏰ *No es horario de tutoría*\n\n"
                    f"El profesor {escape_markdown(sala['NombreProfesor'])} {escape_markdown(sala['ApellidosProfesor'] or '')} "
                    f"tiene el siguiente horario de tutorías:\n\n"
                    f"{escape_markdown(sala['HorarioProfesor'])}\n\n"
                    f"Por favor, intenta solicitar acceso durante estos horarios.",
                    parse_mode="Markdown"
                )
                return
            
            # 4. Estamos en horario de tutoría, enviar notificación al profesor
            # Obtener datos del estudiante para la notificación
            estudiante_nombre = f"{user['Nombre']} {user['Apellidos'] or ''}".strip()
            
            # Crear mensaje de notificación para el profesor
            mensaje_profesor = (
                f"🔔 *Solicitud de tutoría privada*\n\n"
                f"👤 Estudiante: {escape_markdown(estudiante_nombre)}\n"
                f"📧 Email: {escape_markdown(user['Email_UGR'] or 'No disponible')}\n"
            )
            
            if sala['NombreAsignatura']:
                mensaje_profesor += f"📚 Asignatura: {escape_markdown(sala['NombreAsignatura'])}\n"
            
            mensaje_profesor += (
                f"\nEl estudiante ha solicitado acceso a tu sala de tutorías privadas."
            )
            
            # Crear botones para que el profesor pueda aprobar o rechazar
            markup_profesor = types.InlineKeyboardMarkup(row_width=2)
            markup_profesor.add(
                types.InlineKeyboardButton("✅ Aprobar", callback_data=f"aprobar_tutoria_{sala_id}_{user['Id_usuario']}"),
                types.InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar_tutoria_{sala_id}_{user['Id_usuario']}")
            )
            
            # 5. Generar mensaje de confirmación para el estudiante (sin enviar enlace todavía)
            if sala['Enlace_invitacion']:
                # Mensaje para el estudiante (solo confirmación de solicitud)
                mensaje_estudiante = (
                    f"✅ *Solicitud de tutoría enviada*\n\n"
                    f"Tu solicitud ha sido enviada al profesor "
                    f"{escape_markdown(sala['NombreProfesor'])} {escape_markdown(sala['ApellidosProfesor'] or '')}.\n\n"
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
                    "⚠️ Esta sala no tiene un enlace de invitación configurado. "
                    "El profesor deberá proporcionarte el acceso manualmente si aprueba tu solicitud.",
                    parse_mode="Markdown"
                )
            
            # 6. Enviar la notificación al profesor
            if sala['ProfesorTelegramID']:
                bot.send_message(
                    sala['ProfesorTelegramID'],
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
            logger.error(f"Error al procesar solicitud de sala: {e}")
            bot.answer_callback_query(call.id, "❌ Ha ocurrido un error al procesar tu solicitud.")
            bot.send_message(chat_id, "Lo sentimos, ha ocurrido un error al procesar tu solicitud de tutoría.")
        
        print("### FIN SOLICITAR_SALA ###\n")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("aprobar_tutoria_"))
    def handle_aprobar_tutoria(call):
        """Maneja la aprobación de una solicitud de tutoría privada"""
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
                
            sala_id = int(parts[2])
            estudiante_id = int(parts[3])
            
            # 1. Verificar que el usuario que aprueba es el profesor propietario de la sala
            profesor = get_user_by_telegram_id(user_id)
            if not profesor or profesor['Tipo'] != 'profesor':
                bot.answer_callback_query(call.id, "⚠️ Solo el profesor propietario puede aprobar solicitudes.")
                return
            
            # 2. Obtener información de la sala y del estudiante
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar que la sala pertenece al profesor
            cursor.execute("""
                SELECT g.*, u.Nombre as NombreProfesor, u.Apellidos as ApellidosProfesor
                FROM Grupos_tutoria g
                JOIN Usuarios u ON g.Id_usuario = u.Id_usuario
                WHERE g.id_sala = ? AND g.Id_usuario = (
                    SELECT Id_usuario FROM Usuarios WHERE TelegramID = ?
                )
            """, (sala_id, user_id))
            
            sala = cursor.fetchone()
            
            if not sala:
                bot.answer_callback_query(call.id, "❌ No tienes permisos para esta sala o no existe.")
                conn.close()
                return
            
            # 3. Obtener información del estudiante
            cursor.execute("""
                SELECT * 
                FROM Usuarios 
                WHERE Id_usuario = ? AND Tipo = 'estudiante'
            """, (estudiante_id,))
            
            estudiante = cursor.fetchone()
            
            if not estudiante:
                bot.answer_callback_query(call.id, "❌ No se encontró al estudiante.")
                conn.close()
                return
            
            # 4. Verificar si el estudiante ya es miembro de la sala
            cursor.execute("""
                SELECT * FROM Miembros_Grupo 
                WHERE id_sala = ? AND Id_usuario = ?
            """, (sala_id, estudiante_id))
            
            miembro_existente = cursor.fetchone()
            
            if miembro_existente:
                # Actualizar estado a activo si estaba inactivo
                cursor.execute("""
                    UPDATE Miembros_Grupo 
                    SET Estado = 'activo' 
                    WHERE id_sala = ? AND Id_usuario = ?
                """, (sala_id, estudiante_id))
            else:
                # Añadir al estudiante como miembro de la sala
                cursor.execute("""
                    INSERT INTO Miembros_Grupo (id_sala, Id_usuario, Estado)
                    VALUES (?, ?, 'activo')
                """, (sala_id, estudiante_id))
        
            conn.commit()
            
            # 5. Enviar enlace de invitación al estudiante
            if sala['Enlace_invitacion'] and estudiante['TelegramID']:
                mensaje_estudiante = (
                    f"✅ *Tu solicitud de tutoría ha sido aprobada*\n\n"
                    f"El profesor {escape_markdown(profesor['Nombre'])} {escape_markdown(profesor['Apellidos'] or '')} "
                    f"ha aprobado tu solicitud de acceso a la sala de tutorías.\n\n"
                    f"Usa este enlace para unirte al grupo: {sala['Enlace_invitacion']}"
                )
                
                bot.send_message(
                    estudiante['TelegramID'],
                    mensaje_estudiante,
                    parse_mode="Markdown"
                )
                print(f"✅ Enlace de invitación enviado al estudiante {estudiante['Id_usuario']}")
            else:
                # Si no hay enlace o ID de Telegram
                bot.send_message(
                    chat_id,
                    f"⚠️ No se pudo enviar el enlace de invitación a {estudiante['Nombre']} {estudiante['Apellidos'] or ''}.\n"
                    f"Verifique que la sala tenga un enlace de invitación configurado."
                )
        
            # 6. Actualizar el mensaje de solicitud para mostrar que fue aprobada
            nombre_completo = f"{estudiante['Nombre']} {estudiante['Apellidos'] or ''}".strip()
            
            mensaje_actualizado = (
                f"✅ *Solicitud APROBADA*\n\n"
                f"👤 Estudiante: {escape_markdown(nombre_completo)}\n"
                f"📧 Email: {escape_markdown(estudiante['Email_UGR'] or 'No disponible')}\n\n"
                f"Acceso concedido a la sala: {escape_markdown(sala['Nombre_sala'])}"
            )
            
            # Eliminar los botones de aprobar/rechazar
            bot.edit_message_text(
                mensaje_actualizado,
                chat_id=chat_id,
                message_id=call.message.message_id,
                parse_mode="Markdown"
            )
            
            bot.answer_callback_query(call.id, "✅ Solicitud aprobada con éxito")
            
            print(f"✅ Solicitud de tutoría aprobada: Estudiante {estudiante_id} añadido a sala {sala_id}")
            
        except Exception as e:
            print(f"❌ Error al aprobar solicitud: {e}")
            import traceback
            traceback.print_exc()
            bot.answer_callback_query(call.id, "❌ Ha ocurrido un error al procesar la aprobación")
    
        print("### FIN APROBAR_TUTORIA ###\n")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("rechazar_tutoria_"))
    def handle_rechazar_tutoria(call):
        """Maneja el rechazo de una solicitud de tutoría privada"""
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        
        print(f"\n### INICIO RECHAZAR_TUTORIA ###")
        print(f"Chat ID: {chat_id}, User ID: {user_id}")
        print(f"Callback data: {call.data}")
        
        try:
            # Extraer los IDs necesarios del callback_data
            # Formato: rechazar_tutoria_sala_estudiante
            parts = call.data.split("_")
            if len(parts) < 4:
                bot.answer_callback_query(call.id, "❌ Formato de solicitud incorrecto.")
                return
                
            sala_id = int(parts[2])
            estudiante_id = int(parts[3])
            
            # Verificar que el usuario que rechaza es el profesor propietario de la sala
            profesor = get_user_by_telegram_id(user_id)
            if not profesor or profesor['Tipo'] != 'profesor':
                bot.answer_callback_query(call.id, "⚠️ Solo el profesor propietario puede rechazar solicitudes.")
                return
            
            # Obtener información del estudiante y la sala
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM Usuarios WHERE Id_usuario = ?
            """, (estudiante_id,))
            estudiante = cursor.fetchone()
            
            cursor.execute("""
                SELECT * FROM Grupos_tutoria WHERE id_sala = ?
            """, (sala_id,))
            sala = cursor.fetchone()
            
            conn.close()
            
            if not estudiante or not sala:
                bot.answer_callback_query(call.id, "❌ Datos de solicitud no encontrados.")
                return
            
            # Actualizar el mensaje para mostrar que fue rechazada
            nombre_completo = f"{estudiante['Nombre']} {estudiante['Apellidos'] or ''}".strip()
            
            mensaje_actualizado = (
                f"❌ *Solicitud RECHAZADA*\n\n"
                f"👤 Estudiante: {escape_markdown(nombre_completo)}\n"
                f"📧 Email: {escape_markdown(estudiante['Email_UGR'] or 'No disponible')}\n\n"
                f"Acceso denegado a la sala: {escape_markdown(sala['Nombre_sala'])}"
            )
            
            # Eliminar los botones de aprobar/rechazar
            bot.edit_message_text(
                mensaje_actualizado,
                chat_id=chat_id,
                message_id=call.message.message_id,
                parse_mode="Markdown"
            )
            
            # Notificar al estudiante si tiene Telegram registrado
            if estudiante['TelegramID']:
                mensaje_rechazo = (
                    f"❌ *Tu solicitud de tutoría ha sido rechazada*\n\n"
                    f"El profesor {escape_markdown(profesor['Nombre'])} {escape_markdown(profesor['Apellidos'] or '')} "
                    f"ha rechazado tu solicitud de acceso a la sala de tutorías.\n\n"
                    f"Si necesitas más información, contacta directamente con el profesor."
                )
                
                bot.send_message(
                    estudiante['TelegramID'],
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


def registrar_solicitud_tutoria(estudiante_id, profesor_id, sala_id):
    """
    Registra una solicitud de tutoría en la base de datos
    
    Args:
        estudiante_id (int): ID del estudiante que solicita
        profesor_id (int): ID del profesor
        sala_id (int): ID de la sala solicitada
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si ya existe un registro de este estudiante en esta sala
        cursor.execute(
            "SELECT id_miembro FROM Miembros_Grupo WHERE id_sala = ? AND Id_usuario = ?",
            (sala_id, estudiante_id)
        )
        
        miembro = cursor.fetchone()
        
        if miembro:
            # Si ya existe, actualizar su estado a activo si no lo está
            cursor.execute(
                "UPDATE Miembros_Grupo SET Estado = 'activo' WHERE id_miembro = ?",
                (miembro['id_miembro'],)
            )
        else:
            # Si no existe, crear un nuevo registro
            cursor.execute(
                """
                INSERT INTO Miembros_Grupo (id_sala, Id_usuario, Estado)
                VALUES (?, ?, 'pendiente')
                """,
                (sala_id, estudiante_id)
            )
        
        conn.commit()
        conn.close()
        print(f"✅ Solicitud registrada: Estudiante {estudiante_id} para sala {sala_id}")
        
    except Exception as e:
        print(f"❌ Error al registrar solicitud de tutoría: {e}")