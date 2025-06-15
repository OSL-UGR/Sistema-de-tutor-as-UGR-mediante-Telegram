import telebot
import time
import threading
from telebot import types
import os
import sys
from config import TOKEN, DB_PATH,EXCEL_PATH

# Importar funciones para manejar estados
from utils.state_manager import get_state, set_state, clear_state, user_states, user_data

# Importar funciones para manejar el Excel
from utils.excel_manager import cargar_excel, importar_datos_desde_excel
from db.queries import get_db_connection
# Reemplaza todos los handlers universales por este ÚNICO handler al final
# Inicializar el bot de Telegram
bot = telebot.TeleBot(TOKEN) 

def escape_markdown(text):
    """Escapa caracteres especiales de Markdown"""
    if not text:
        return ""
    
    chars = ['_', '*', '`', '[', ']', '(', ')', '#', '+', '-', '.', '!']
    for char in chars:
        text = text.replace(char, '\\' + char)
    
    return text




def setup_commands():
    """Configura los comandos que aparecen en el menú del bot"""
    try:
        bot.set_my_commands([
            telebot.types.BotCommand("/start", "Inicia el bot y el registro"),
            telebot.types.BotCommand("/help", "Muestra la ayuda del bot"),
            telebot.types.BotCommand("/tutoria", "Ver profesores disponibles para tutoría"),
            telebot.types.BotCommand("/crear_grupo_tutoria", "Crea un grupo de tutoría"),
            telebot.types.BotCommand("/configurar_horario", "Configura tu horario de tutorías"),
            telebot.types.BotCommand("/ver_misdatos", "Ver tus datos registrados")
        ])
        print("✅ Comandos del bot configurados correctamente")
        return True
    except Exception as e:
        print(f"❌ Error al configurar los comandos del bot: {e}")
        return False

# Importar funciones básicas de consulta a la BD
from db.queries import get_user_by_telegram_id

@bot.message_handler(commands=['help'])
def handle_help(message):
    """Muestra la ayuda del bot"""
    chat_id = message.chat.id
    user = get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        bot.send_message(
            chat_id,
            "❌ No estás registrado. Usa /start para registrarte."
        )
        return
    
    help_text = (
        "🤖 *Comandos disponibles:*\n\n"
        "/start - Inicia el bot y el proceso de registro\n"
        "/help - Muestra este mensaje de ayuda\n"
        "/tutoria - Ver profesores disponibles para tutoría\n"
        "/ver_misdatos - Ver tus datos registrados\n"
    )
    
    if user['Tipo'] == 'profesor':
        help_text += (
            "/configurar_horario - Configura tu horario de tutorías\n"
            "/crear_grupo_tutoria - Crea un grupo de tutoría\n"
        )
    
    # Escapar los guiones bajos para evitar problemas de formato
    help_text = help_text.replace("_", "\\_")
    
    try:
        bot.send_message(chat_id, help_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Error al enviar mensaje de ayuda: {e}")
        # Si falla, envía sin formato
        bot.send_message(chat_id, help_text.replace('*', ''), parse_mode=None)

@bot.message_handler(commands=['ver_misdatos'])
def handle_ver_misdatos(message):
    chat_id = message.chat.id
    print(f"\n\n### INICIO VER_MISDATOS - Usuario: {message.from_user.id} ###")
    
    user = get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        print("⚠️ Usuario no encontrado en BD")
        bot.send_message(chat_id, "❌ No estás registrado. Usa /start para registrarte.")
        return
    
    print(f"✅ Usuario encontrado: {user['Nombre']} ({user['Tipo']})")
    
    # Convertir el objeto sqlite3.Row a diccionario
    user_dict = dict(user)
    
    # Obtener matrículas del usuario
    from db.queries import get_matriculas_usuario
    matriculas = get_matriculas_usuario(user['Id_usuario'])
    
    user_info = (
        f"👤 *Datos de usuario:*\n\n"
        f"*Nombre:* {user['Nombre']}\n"
        f"*Correo:* {user['Email_UGR'] or 'No registrado'}\n"
        f"*Tipo:* {user['Tipo'].capitalize()}\n"
    )
    
    # Añadir la carrera desde la tabla Usuarios
    if 'Carrera' in user_dict and user_dict['Carrera']:
        user_info += f"*Carrera:* {user_dict['Carrera']}\n\n"
    else:
        user_info += "*Carrera:* No registrada\n\n"
    
    # Añadir información de matrículas
    if matriculas and len(matriculas) > 0:
        user_info += "*Asignaturas matriculadas:*\n"
        
        # Agrupar asignaturas por carrera
        for m in matriculas:
            # Convertir cada matrícula a diccionario si es necesario
            m_dict = dict(m) if hasattr(m, 'keys') else m
            asignatura = m_dict.get('Asignatura', 'Desconocida')
            user_info += f"- {asignatura}\n"
    else:
        user_info += "No tienes asignaturas matriculadas.\n"
    
    # Añadir horario si es profesor
    if user['Tipo'] == 'profesor':
        if 'Horario' in user_dict and user_dict['Horario']:
            user_info += f"\n*Horario de tutorías:*\n{user_dict['Horario']}\n\n"
        
        # NUEVA SECCIÓN: Mostrar salas creadas por el profesor
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Consultar todas las salas creadas por este profesor
        cursor.execute("""
            SELECT g.Nombre_sala, g.Proposito_sala, g.Tipo_sala, g.Fecha_creacion, 
                   g.id_sala, g.Chat_id, a.Nombre as NombreAsignatura
            FROM Grupos_tutoria g
            LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
            WHERE g.Id_usuario = ?
            ORDER BY g.Fecha_creacion DESC
        """, (user['Id_usuario'],))
        
        salas = cursor.fetchall()
        conn.close()
        
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
                asignatura = sala['NombreAsignatura'] or 'General'
                
                # Formato de fecha más amigable
                fecha = sala['Fecha_creacion'].split(' ')[0] if sala['Fecha_creacion'] else 'Desconocida'
                
                user_info += f"• *{sala['Nombre_sala']}*\n"
                user_info += f"  📋 Propósito: {proposito}\n"
                user_info += f"  📚 Asignatura: {asignatura}\n"
                user_info += f"  📅 Creada: {fecha}\n\n"
        else:
            user_info += "\n*🔵 No has creado salas de tutoría todavía.*\n"
            user_info += "Usa /crear_grupo_tutoria para crear una nueva sala.\n"
    
    # Intentar enviar el mensaje con formato Markdown
    try:
        bot.send_message(chat_id, user_info, parse_mode="Markdown")
        
        # Si es profesor y tiene salas, mostrar botones para editar
        if user['Tipo'] == 'profesor' and salas and len(salas) > 0:
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
        # Si falla por problemas de formato, enviar sin formato
        print(f"Error al enviar datos de usuario: {e}")
        bot.send_message(chat_id, user_info.replace('*', ''), parse_mode=None)

# Importar y configurar los handlers desde los módulos
from handlers.registro import register_handlers as register_registro_handlers
from handlers.tutorias import register_handlers as register_tutorias_handlers
from handlers.horarios import register_handlers as register_horarios_handlers
from utils.excel_manager import verificar_excel_disponible
from grupo_handlers.grupos import GestionGrupos

# Verificar si es la primera ejecución
MARKER_FILE = os.path.join(os.path.dirname(DB_PATH), ".initialized")
primera_ejecucion = not os.path.exists(MARKER_FILE)

# Verificar que el Excel existe pero no cargar datos
print("📊 Cargando datos académicos...")
if verificar_excel_disponible():
    print("✅ Excel encontrado")
    # Primera vez - importar todo
    if primera_ejecucion:  # Usa alguna forma de detectar primer inicio
        importar_datos_desde_excel(solo_nuevos=False)
        # Crear archivo marcador para futuras ejecuciones
        with open(MARKER_FILE, 'w') as f:
            f.write("Initialized")
    else:
        # Ejecuciones posteriores - solo nuevos datos
        importar_datos_desde_excel(solo_nuevos=True)
else:
    print("⚠️ Excel no encontrado")

# Registrar todos los handlers
register_registro_handlers(bot)
register_tutorias_handlers(bot)
register_horarios_handlers(bot)


# Handlers para cambio de propósito de salas de tutoría
@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_sala_"))
def handle_edit_sala(call):
    """Muestra opciones para editar una sala"""
    chat_id = call.message.chat.id
    print(f"\n\n### INICIO EDIT_SALA - Callback: {call.data} ###")
    
    try:
        sala_id = int(call.data.split("_")[2])
        print(f"🔍 Sala ID a editar: {sala_id}")
        
        # Verificar que el usuario es el propietario de la sala
        user = get_user_by_telegram_id(call.from_user.id)
        print(f"👤 Usuario: {user['Nombre'] if user else 'No encontrado'}")
        
        if not user or user['Tipo'] != 'profesor':
            print("⚠️ Usuario no es profesor o no existe")
            bot.answer_callback_query(call.id, "⚠️ Solo los profesores propietarios pueden editar salas")
            return
        
        # Obtener datos actuales de la sala
        conn = get_db_connection()
        cursor = conn.cursor()
        print(f"🔍 Consultando detalles de sala ID {sala_id}")
        cursor.execute(
            """
            SELECT g.*, a.Nombre as NombreAsignatura
            FROM Grupos_tutoria g
            LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
            WHERE g.id_sala = ? AND g.Id_usuario = ?  
            """, 
            (sala_id, user['Id_usuario'])
        )
        sala = cursor.fetchone()
        conn.close()
        
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
        nombre_asignatura = escape_markdown(sala['NombreAsignatura'] or 'General')
        
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

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancelar_edicion_"))
def handle_cancelar_edicion(call):
    """Cancela la edición de la sala"""
    bot.edit_message_text(
        "❌ Operación cancelada. No se realizaron cambios.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cambiar_proposito_"))
def handle_cambiar_proposito(call):
    """Muestra opciones para gestionar miembros al cambiar el propósito de la sala"""
    chat_id = call.message.chat.id
    data = call.data.split("_")
    sala_id = int(data[2])
    nuevo_proposito = data[3]
    
    # Verificar usuario
    user = get_user_by_telegram_id(call.from_user.id)
    if not user or user['Tipo'] != 'profesor':
        bot.answer_callback_query(call.id, "⚠️ No tienes permisos para esta acción")
        return
    
    # Obtener datos de la sala
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT g.*, a.Nombre as NombreAsignatura
        FROM Grupos_tutoria g
        LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
        WHERE g.id_sala = ? AND g.Id_usuario = ?  
        """, 
        (sala_id, user['Id_usuario'])
    )
    sala = cursor.fetchone()
    
    # Contar miembros actuales
    cursor.execute(
        "SELECT COUNT(*) as total FROM Miembros_Grupo WHERE id_sala = ? AND Estado = 'activo'",  # cambiar chat_id por id_sala
        (sala_id,)
    )
    miembros = cursor.fetchone()
    conn.close()
    
    total_miembros = miembros['total'] if miembros else 0
    
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
    nombre_asignatura = escape_markdown(sala['NombreAsignatura'] or 'General')
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

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirmar_cambio_"))
def handle_confirmar_cambio(call):
    """Confirma el cambio de propósito con la decisión sobre los miembros"""
    chat_id = call.message.chat.id
    data = call.data.split("_")
    sala_id = int(data[2])
    nuevo_proposito = data[3]
    decision_miembros = data[4]  # "mantener" o "eliminar"
    
    # Verificar usuario
    user = get_user_by_telegram_id(call.from_user.id)
    if not user or user['Tipo'] != 'profesor':
        bot.answer_callback_query(call.id, "⚠️ No tienes permisos para esta acción")
        return
    
    # Realizar el cambio de propósito
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener información de la sala
        cursor.execute(
            """
            SELECT g.*, a.Nombre as NombreAsignatura, u.Nombre as NombreProfesor
            FROM Grupos_tutoria g
            LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
            LEFT JOIN Usuarios u ON g.Id_usuario = u.Id_usuario
            WHERE g.id_sala = ?
            """, 
            (sala_id,)
        )
        sala = cursor.fetchone()
        
        if not sala:
            bot.answer_callback_query(call.id, "❌ Error: No se encontró la sala")
            conn.close()
            return
        
        # 1. Actualizar el propósito de la sala
        cursor.execute(
            "UPDATE Grupos_tutoria SET Proposito_sala = ? WHERE id_sala = ? AND Id_usuario = ?",
            (nuevo_proposito, sala_id, user['Id_usuario'])
        )
        
        # 2. Actualizar el tipo de sala según el propósito
        tipo_sala = 'pública' if nuevo_proposito == 'avisos' else 'privada'
        cursor.execute(
            "UPDATE Grupos_tutoria SET Tipo_sala = ? WHERE id_sala = ?",
            (tipo_sala, sala_id)
        )
        
        # 3. Generar y actualizar el nuevo nombre según el propósito
        nuevo_nombre = None
        if nuevo_proposito == 'avisos':
            nuevo_nombre = f"Avisos: {sala['NombreAsignatura']}"
        elif nuevo_proposito == 'individual':
            nuevo_nombre = f"Tutoría Privada - Prof. {sala['NombreProfesor']}"
        
        # Actualizar el nombre en la BD
        if nuevo_nombre:
            cursor.execute(
                "UPDATE Grupos_tutoria SET Nombre_sala = ? WHERE id_sala = ?",
                (nuevo_nombre, sala_id)
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
                    from grupo_handlers.grupos import cambiar_nombre_grupo_telegram
                    
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
            cursor.execute(
                """
                DELETE FROM Miembros_Grupo 
                WHERE id_sala = ? AND Id_usuario != (
                    SELECT Id_usuario FROM Grupos_tutoria WHERE id_sala = ?
                )
                """,
                (sala_id, sala_id)
            )
        
        conn.commit()
        
        # Obtener información actualizada de la sala
        cursor.execute(
            """
            SELECT g.*, a.Nombre as NombreAsignatura
            FROM Grupos_tutoria g
            LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
            WHERE g.id_sala = ?
            """, 
            (sala_id,)
        )
        sala = cursor.fetchone()
        
        # Contar miembros restantes
        cursor.execute(
            "SELECT COUNT(*) as total FROM Miembros_Grupo WHERE id_sala = ? AND Estado = 'activo'",
            (sala_id,)
        )
        miembros = cursor.fetchone()
        total_miembros = miembros['total'] if miembros else 0
        
        # Textos para los propósitos
        propositos = {
            'individual': 'Tutorías individuales',
            'grupal': 'Tutorías grupales',
            'avisos': 'Canal de avisos'
        }
        
        # Escapar textos que pueden contener caracteres Markdown
        nombre_sala = escape_markdown(sala['Nombre_sala'])
        nombre_asignatura = escape_markdown(sala['NombreAsignatura'] or 'General')
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
    finally:
        conn.close()
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ver_miembros_"))
def handle_ver_miembros(call):
    """Muestra la lista de miembros de la sala antes de decidir"""
    chat_id = call.message.chat.id
    data = call.data.split("_")
    sala_id = int(data[2])
    nuevo_proposito = data[3]
    
    # Verificar usuario
    user = get_user_by_telegram_id(call.from_user.id)
    if not user or user['Tipo'] != 'profesor':
        bot.answer_callback_query(call.id, "⚠️ No tienes permisos para esta acción")
        return
    
    # Obtener lista de miembros
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT u.Nombre, u.Apellidos, u.Email_UGR, mg.Fecha_union, mg.Estado
        FROM Miembros_Grupo mg
        JOIN Usuarios u ON mg.Id_usuario = u.Id_usuario
        WHERE mg.id_sala = ? AND mg.Estado = 'activo'
        ORDER BY mg.Fecha_union DESC
        """,
        (sala_id,)
    )
    
    miembros = cursor.fetchall()
    
    # Obtener información de la sala
    cursor.execute(
        "SELECT Nombre_sala FROM Grupos_tutoria WHERE id_sala = ?",
        (sala_id,)
    )
    sala = cursor.fetchone()
    conn.close()
    
    if not miembros:
        # No hay miembros, cambiar directamente
        bot.answer_callback_query(call.id, "No hay miembros en esta sala")
        realizar_cambio_proposito(chat_id, call.message.message_id, sala_id, nuevo_proposito, user['Id_usuario'])
        return
    
    # Crear mensaje con lista de miembros
    mensaje = f"👥 *Miembros de la sala \"{sala['Nombre_sala']}\":*\n\n"
    
    for i, m in enumerate(miembros, 1):
        nombre_completo = f"{m['Nombre']} {m['Apellidos'] or ''}"
        fecha = m['Fecha_union'].split(' ')[0] if m['Fecha_union'] else 'Desconocida'
        mensaje += f"{i}. *{nombre_completo}*\n   📧 {m['Email_UGR']}\n   📅 Unido: {fecha}\n\n"
    
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

def notificar_cambio_sala(sala_id, nuevo_proposito):
    """Notifica a los miembros de la sala sobre el cambio de propósito"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener datos de la sala
    cursor.execute(
        """
        SELECT g.*, u.Nombre as NombreProfesor, a.Nombre as NombreAsignatura
        FROM Grupos_tutoria g
        JOIN Usuarios u ON g.Id_usuario = u.Id_usuario
        LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
        WHERE g.id_sala = ?  
        """, 
        (sala_id,)
    )
    sala = cursor.fetchone()
    
    if not sala:
        conn.close()
        return
    
    # Obtener miembros de la sala
    cursor.execute(
        """
        SELECT u.*
        FROM Miembros_Grupo mg
        JOIN Usuarios u ON mg.Id_usuario = u.Id_usuario
        WHERE mg.id_sala = ? AND u.Tipo = 'estudiante' AND mg.Estado = 'activo'  
        """, 
        (sala_id,)
    )
    miembros = cursor.fetchall()
    conn.close()
    
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
    for miembro in miembros:
        if miembro['TelegramID']:
            try:
                bot.send_message(
                    miembro['TelegramID'],
                    f"ℹ️ *Cambio en sala de tutoría*\n\n"
                    f"El profesor *{sala['NombreProfesor']}* ha modificado el propósito "
                    f"de la sala *{sala['Nombre_sala']}*.\n\n"
                    f"*Nuevo propósito:* {propositos.get(nuevo_proposito, 'General')}\n"
                    f"*Asignatura:* {sala['NombreAsignatura'] or 'General'}\n\n"
                    f"{explicaciones.get(nuevo_proposito, '')}\n\n"
                    f"Tu acceso a la sala se mantiene, pero la forma de interactuar "
                    f"podría cambiar según el nuevo propósito.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Error al notificar a usuario {miembro['Id_usuario']}: {e}")

def realizar_cambio_proposito(chat_id, message_id, sala_id, nuevo_proposito, user_id):
    """Realiza el cambio de propósito cuando no hay miembros que gestionar"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Obtener datos actuales de la sala
        cursor.execute(
            """
            SELECT g.*, a.Nombre as NombreAsignatura
            FROM Grupos_tutoria g
            LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
            WHERE g.id_sala = ?
            """, 
            (sala_id,)
        )
        sala = cursor.fetchone()
        
        if not sala:
            bot.edit_message_text(
                "❌ Error: No se encontró la sala",
                chat_id=chat_id,
                message_id=message_id
            )
            conn.close()
            return
        
        # Actualizar propósito
        cursor.execute(
            "UPDATE Grupos_tutoria SET Proposito_sala = ? WHERE id_sala = ? AND Id_usuario = ?",
            (nuevo_proposito, sala_id, user_id)
        )
        
        # Actualizar tipo
        tipo_sala = 'pública' if nuevo_proposito == 'avisos' else 'privada'
        cursor.execute(
            "UPDATE Grupos_tutoria SET Tipo_sala = ? WHERE id_sala = ?",
            (tipo_sala, sala_id)
        )
        
        # Generar nuevo nombre según el propósito
        nuevo_nombre = None
        if nuevo_proposito == 'avisos':
            nuevo_nombre = f"Avisos: {sala['NombreAsignatura']}"
        elif nuevo_proposito == 'individual':
            nuevo_nombre = f"Tutoría Privada - Prof. {obtener_nombre_profesor(user_id)}"
        
        # Si se generó un nuevo nombre, actualizar en la base de datos
        if nuevo_nombre:
            cursor.execute(
                "UPDATE Grupos_tutoria SET Nombre_sala = ? WHERE id_sala = ?",
                (nuevo_nombre, sala_id)
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
                    from grupo_handlers.grupos import cambiar_nombre_grupo_telegram
                    
                    # Llamar a la función para cambiar el nombre
                    if cambiar_nombre_grupo_telegram(telegram_chat_id, nuevo_nombre):
                        print(f"✅ Nombre del grupo actualizado usando el bot de grupos")
                    else:
                        print(f"❌ No se pudo cambiar el nombre del grupo ni siquiera con el bot de grupos")
                except Exception as e:
                    print(f"❌ Error al intentar utilizar la función del bot de grupos: {e}")
        
        conn.commit()
        
        # Obtener info actualizada
        cursor.execute(
            """
            SELECT g.*, a.Nombre as NombreAsignatura
            FROM Grupos_tutoria g
            LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
            WHERE g.id_sala = ?
            """, 
            (sala_id,)
        )
        sala_actualizada = cursor.fetchone()
        
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
            f"*Asignatura:* {sala_actualizada['NombreAsignatura'] or 'General'}\n\n"
            f"La sala está lista para su nuevo propósito.",
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        print(f"Error al actualizar sala: {e}")
        bot.send_message(chat_id, "❌ Error al actualizar la sala")
    finally:
        conn.close()

def obtener_nombre_profesor(user_id):
    """Obtiene el nombre del profesor a partir del id de usuario"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Nombre FROM Usuarios WHERE Id_usuario = ?", (user_id,))
    resultado = cursor.fetchone()
    conn.close()
    return resultado['Nombre'] if resultado else "Profesor"



@bot.callback_query_handler(func=lambda call: call.data.startswith("eliminarsala_"))
def handle_eliminar_sala(call):
    """Maneja la solicitud de eliminación de una sala"""
    chat_id = call.message.chat.id
    print(f"\n\n### INICIO ELIMINAR_SALA - Callback: {call.data} ###")
    
    try:
        sala_id = int(call.data.split("_")[1])
        print(f"🔍 Sala ID a eliminar: {sala_id}")
        
        # Verificar que el usuario es el propietario de la sala
        user = get_user_by_telegram_id(call.from_user.id)
        
        if not user or user['Tipo'] != 'profesor':
            print("⚠️ Usuario no es profesor o no existe")
            bot.answer_callback_query(call.id, "⚠️ Solo los profesores propietarios pueden eliminar salas")
            return
        
        # Obtener datos de la sala
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT g.*, a.Nombre as NombreAsignatura
            FROM Grupos_tutoria g
            LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
            WHERE g.id_sala = ? AND g.Id_usuario = ?  
            """, 
            (sala_id, user['Id_usuario'])
        )
        sala = cursor.fetchone()
        
        if not sala:
            print(f"❌ Sala no encontrada o no pertenece al usuario")
            bot.answer_callback_query(call.id, "❌ No se encontró la sala o no tienes permisos")
            conn.close()
            return
        
        print(f"✅ Sala encontrada: {sala['Nombre_sala']} (Chat ID: {sala['Chat_id']})")
        
        # Contar miembros actuales
        cursor.execute(
            "SELECT COUNT(*) as total FROM Miembros_Grupo WHERE id_sala = ? AND Estado = 'activo'",
            (sala_id,)
        )
        miembros = cursor.fetchone()
        total_miembros = miembros['total'] if miembros else 0
        conn.close()
        
        # Preparar textos seguros para Markdown
        nombre_sala = escape_markdown(sala['Nombre_sala'])
        nombre_asignatura = escape_markdown(sala['NombreAsignatura'] or 'General')
        
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
        user = get_user_by_telegram_id(call.from_user.id)
        
        if not user or user['Tipo'] != 'profesor':
            print("⚠️ Usuario no es profesor o no existe")
            bot.answer_callback_query(call.id, "⚠️ Solo los profesores propietarios pueden eliminar salas")
            return
        
        # Obtener datos de la sala
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT g.*, a.Nombre as NombreAsignatura
            FROM Grupos_tutoria g
            LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
            WHERE g.id_sala = ? AND g.Id_usuario = ?  
            """, 
            (sala_id, user['Id_usuario'])
        )
        sala = cursor.fetchone()
        
        if not sala:
            print(f"❌ Sala no encontrada o no pertenece al usuario")
            bot.answer_callback_query(call.id, "❌ No se encontró la sala o no tienes permisos")
            conn.close()
            return
        
        nombre_sala = sala['Nombre_sala']
        telegram_chat_id = sala['Chat_id']
        print(f"✅ Ejecutando eliminación de sala: {nombre_sala} (ID: {sala_id}, Chat ID: {telegram_chat_id})")
        
        # 1. Eliminar todos los miembros de la sala
        print("1️⃣ Eliminando miembros...")
        cursor.execute(
            "DELETE FROM Miembros_Grupo WHERE id_sala = ?",
            (sala_id,)
        )
        print(f"  ✓ Miembros eliminados de la BD")
        
        # 2. Eliminar la sala de la base de datos
        print("2️⃣ Eliminando registro de sala...")
        cursor.execute(
            "DELETE FROM Grupos_tutoria WHERE id_sala = ? AND Id_usuario = ?",
            (sala_id, user['Id_usuario'])
        )
        print(f"  ✓ Sala eliminada de la BD")
        
        # Confirmar cambios en la base de datos
        conn.commit()
        conn.close()
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
                from grupo_handlers.grupos import salir_de_grupo
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

@bot.message_handler(commands=['crear_grupo_tutoria'])
def crear_grupo(message):
    """Proporciona instrucciones para crear un grupo de tutoría en Telegram"""
    chat_id = message.chat.id
    user = get_user_by_telegram_id(message.from_user.id)
    
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
            callback_data="ver_misdatos"  # Simplificado
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


# Handlers para los botones simplificados
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
    
    # Solución para evitar crear un mensaje simulado
    try:
        print("🔄 Llamando directamente a handle_ver_misdatos...")
        
        # En lugar de crear un mensaje simulado, llamamos directamente a la función
        # y proporcionamos los datos mínimos necesarios
        mensaje_directo = {
            'chat': {'id': chat_id},
            'from_user': {'id': user_id},
            'text': '/ver_misdatos'
        }
        
        # Creamos una versión simplificada del mensaje
        class SimpleMessage:
            def __init__(self, chat_id, user_id, text):
                self.chat = types.Chat(chat_id, 'private')
                self.from_user = types.User(user_id, False, 'Usuario')
                self.text = text
        
        # Crear el mensaje simplificado
        msg = SimpleMessage(chat_id, user_id, '/ver_misdatos')
        
        # Llamar directamente a la función de manejo
        handle_ver_misdatos(msg)
        print("✅ handle_ver_misdatos llamado con éxito")
    except Exception as e:
        print(f"❌ Error al llamar a handle_ver_misdatos: {str(e)}")
        import traceback
        print("📋 Traza de error completa:")
        traceback.print_exc()
        bot.send_message(chat_id, "❌ Error al mostrar tus salas. Intenta usar /ver_misdatos directamente.")
    
    print("### FIN VER_SALAS CALLBACK ###\n\n")


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

# Añadir al final del archivo, después de la función obtener_nombre_profesor

def setup_polling():
    """Configura el polling para el bot y maneja errores"""
    print("🤖 Iniciando el bot...")
    try:
        # Configurar comandos disponibles
        if setup_commands():
            print("✅ Comandos configurados correctamente")
        else:
            print("⚠️ Error al configurar comandos")
        
        # Agregar esta línea:
        print("⚙️ Configurando polling con eventos de grupo...")
        
        # Modificar esta línea:
        bot.infinity_polling(
            timeout=10, 
            long_polling_timeout=5,
            allowed_updates=["message", "callback_query", "my_chat_member", "chat_member"]
        )
    except KeyboardInterrupt:
        print("👋 Bot detenido manualmente")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        
        # Reintentar después de un tiempo
        print("🔄 Reintentando en 10 segundos...")
        time.sleep(10)
        setup_polling()

if __name__ == "__main__":
    print("="*50)
    print("🎓 SISTEMA DE TUTORÍAS UGR")
    print("="*50)
    print(f"📅 Fecha de inicio: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💾 Base de datos: {DB_PATH}")
    print(f"📊 Excel de datos: {EXCEL_PATH}")
    print("="*50)
    
    # Iniciar el bot
    setup_polling()
