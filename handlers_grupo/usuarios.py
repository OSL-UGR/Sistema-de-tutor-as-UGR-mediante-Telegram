"""
Manejadores específicos para la detección de estudiantes nuevos en grupos.
Este módulo se encarga exclusivamente de dar la bienvenida a estudiantes
cuando entran a un grupo donde está el bot.
"""
from telebot import types
import logging
import os
import sys

from handlers_grupo.utils import configurar_logger
from utils.state_manager import set_state
from db.queries import get_grupos_tutoria
from db.constantes import *

# Configuración de ruta para importar correctamente
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar logging
logger = configurar_logger()

def register_handlers(bot):
    """Registra los handlers para gestionar nuevos estudiantes."""
    print("\n==================================================")
    print("👨‍🎓👨‍🎓👨‍🎓 REGISTRANDO HANDLER DE NUEVOS ESTUDIANTES 👨‍🎓👨‍🎓👨‍🎓")
    print("==================================================\n")
    
    # Importar la función correcta desde utils
    from handlers_grupo.utils import menu_estudiante, menu_profesor
    
    # ID del bot para comparaciones
    global BOT_ID
    try:
        BOT_ID = bot.get_me().id
        print(f"👾 ID del bot: {BOT_ID}")
    except Exception as e:
        print(f"No se pudo obtener ID del bot: {e}")
        BOT_ID = None

    @bot.chat_member_handler()
    def handle_chat_member_update(update):
        """Procesa actualizaciones de miembros del chat (entrar/salir)"""
        try:
            chat_id = update.chat.id
            user = update.new_chat_member.user
            old_status = update.old_chat_member.status
            new_status = update.new_chat_member.status
            
            print(f"\n🔄 CAMBIO DE ESTADO DE MIEMBRO EN CHAT {chat_id}")
            print(f"👤 Usuario: {user.first_name} (ID: {user.id})")
            print(f"📊 Estado: {old_status} -> {new_status}")
            
            # Detectar si un usuario se unió al grupo (cambio de 'left' a 'member')
            if old_status == "left" and new_status == "member":
                print(f"🎓 NUEVO MIEMBRO DETECTADO: {user.first_name}")
                
                # Ignorar si es el propio bot
                if user.id == BOT_ID:
                    print(f"🤖 Es el propio bot, ignorando")
                    return
                
                # A partir de aquí, código similar al que ya tienes en handle_new_student_in_group
                # pero adaptado para trabajar con el objeto update de chat_member
                
                # Obtener información del grupo                
                # Verificar si el grupo es un grupo de tutorías
                grupo = get_grupos_tutoria(GRUPO_ID_CHAT=str(chat_id))[0]
                
                try:
                    if(grupo[GRUPO_TIPO] == GRUPO_PRIVADO):
                        print(f"📨 Intentando enviar mensaje de bienvenida para {user.first_name}")
                        mensaje = bot.send_message(
                            chat_id,
                            f"👋 Bienvenido/a {user.first_name} al grupo.\n\n"
                            f"Cuando termines tu consulta, usa el botón o /finalizar para finalizar la tutoría.",
                            reply_markup=menu_estudiante()  # Usa la función correcta importada de utils
                        )
                        print(f"✅ Mensaje enviado con ID: {mensaje.message_id}")
                        set_state(chat_id,user.id)
                except Exception as e:
                    print(f"❌ ERROR enviando mensaje de bienvenida: {e}")
                    import traceback
                    traceback.print_exc()
                
                if not grupo:
                    print(f"ℹ️ Grupo {chat_id} no es una grupo de tutoría - No se procesa más")
                    return
                
                # Si llegamos aquí, el grupo es una grupo de tutoría registrada
                # Continúa con la lógica para grupos registrados
                
                # ...resto de tu código para grupos registrados...
                
                
        except Exception as e:
            print(f"❌ ERROR PROCESANDO CHAT_MEMBER: {e}")
            import traceback
            traceback.print_exc()
    
    # Handler para new_chat_members (mantenerlo por compatibilidad)
    @bot.message_handler(content_types=['new_chat_members'])
    def handle_new_student_in_group(message):
        """Handler para gestionar el contenido de tipo new_chat_members"""
        print("🎓 HANDLER NEW_CHAT_MEMBERS ACTIVADO")
        try:
            chat_id = message.chat.id
            
            # Imprimir para depuración
            print(f"👥 Procesando nuevos miembros en chat {chat_id}")
            print(f"👥 Mensaje ID: {message.message_id}")
            
            # Procesar cada nuevo miembro
            for new_member in message.new_chat_members:
                user_id = new_member.id
                
                # Ignorar si es el propio bot
                if BOT_ID and user_id == BOT_ID:
                    print(f"🤖 Es el propio bot, ignorando")
                    continue
                    
                print(f"👤 Procesando estudiante: {new_member.first_name} (ID: {user_id})")
                
                # Verificar si el grupo es de tutorías
                grupo = get_grupos_tutoria(GRUPO_ID_CHAT=str(chat_id))[0]

                if not grupo:
                    print(f"ℹ️ Grupo {chat_id} no es una grupo de tutoría - No se procesa más")
                    continue
                
                # Enviar mensaje de bienvenida siempre
                try:
                    if(grupo[GRUPO_TIPO] == GRUPO_PRIVADO):
                        print(f"📨 Intentando enviar mensaje de bienvenida para {new_member.first_name}")
                        mensaje = bot.send_message(
                            chat_id,
                            f"👋 Bienvenido/a {new_member.first_name} al grupo.\n\n"
                            f"Cuando termines tu consulta, usa el botón o /finalizar para finalizar la tutoría.",
                            reply_markup=menu_estudiante()  # Usa la función correcta importada de utils
                        )
                        set_state(chat_id,user_id)
                        print(f"✅ Mensaje enviado con ID: {mensaje.message_id}")
                except Exception as e:
                    print(f"❌ ERROR enviando mensaje de bienvenida: {e}")
                    import traceback
                    traceback.print_exc()
                    
                # Resto de tu lógica para grupos registrados
                # ...
                
                
        except Exception as e:
            print(f"❌ ERROR GENERAL EN HANDLER NEW_CHAT_MEMBERS: {e}")
            import traceback
            traceback.print_exc()