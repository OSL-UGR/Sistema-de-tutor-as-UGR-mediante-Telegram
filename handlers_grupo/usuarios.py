"""
Manejadores específicos para la detección de estudiantes nuevos en grupos.
Este módulo se encarga exclusivamente de dar la bienvenida a estudiantes
cuando entran a un grupo donde está el bot.
"""
import os
import sys

from handlers_grupo.tutorias import COMMAND_FINALIZAR
from handlers_grupo.utils import configurar_logger
from utils.state_manager import *
from db.queries import get_grupos_tutoria, update_grupo_tutoria
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
    from handlers_grupo.utils import menu_estudiante
    
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

                user_id = user.id
                
                # Ignorar si es el propio bot
                if BOT_ID and user_id == BOT_ID:
                    print(f"🤖 Es el propio bot, ignorando")
                    return

                print(f"👤 Procesando estudiante: {user.first_name} (ID: {user_id})")

                # Verificar si el grupo es de tutorías
                grupo = get_grupos_tutoria(GRUPO_ID_CHAT=str(chat_id))[0]
                if not grupo:
                    print(f"ℹ️ Grupo {chat_id} no es una grupo de tutoría - No se procesa más")
                    return

                # Enviar mensaje de bienvenida siempre
                try:
                    if(grupo[GRUPO_TIPO] == GRUPO_PRIVADO):
                        print(f"📨 Intentando enviar mensaje de bienvenida para {user.first_name}")
                        mensaje = bot.send_message(
                            chat_id,
                            f"👋 Bienvenido/a {user.first_name} al grupo.\n\n"
                            f"Cuando termines tu consulta, usa el botón o /{COMMAND_FINALIZAR} para finalizar la tutoría.",
                            reply_markup=menu_estudiante()  # Usa la función correcta importada de utils
                        )
                        set_state(chat_id,user_id)
                        print(f"✅ Mensaje enviado con ID: {mensaje.message_id}")

                        enlace_invitacion = bot.create_chat_invite_link(chat_id, member_limit=1).invite_link
                        update_grupo_tutoria(grupo[GRUPO_ID], GRUPO_ENLACE=enlace_invitacion, GRUPO_EN_USO=True)
                        bot.revoke_chat_invite_link(chat_id, grupo[GRUPO_ENLACE])

                except Exception as e:
                    print(f"❌ ERROR enviando mensaje de bienvenida: {e}")
                    import traceback
                    traceback.print_exc()
        
            elif old_status == "member" and new_status == "left":

                user_id = user.id
                
                # Ignorar si es el propio bot
                if BOT_ID and user_id == BOT_ID:
                    print(f"🤖 Es el propio bot, ignorando")
                    return

                print(f"👤 Procesando estudiante: {user.first_name} (ID: {user_id})")

                # Verificar si el grupo es de tutorías
                grupo = get_grupos_tutoria(GRUPO_ID_CHAT=str(chat_id))[0]
                if not grupo:
                    print(f"ℹ️ Grupo {chat_id} no es una grupo de tutoría - No se procesa más")
                    return

                try:
                    # Obtener el nombre del estudiante
                    nombre = user.first_name
                    if user.last_name:
                        nombre += f" {user.last_name}"
                    # Informar en el grupo
                    bot.send_message(
                        chat_id,
                        f"✅ Ha finalizado su sesión de tutoría con {nombre}."
                    )
                    # Informar por dm
                    bot.send_message(
                        user_id,
                        "👋 Has finalizado tu sesión de tutoría. ¡Gracias por participar!"
                    )
                except Exception as dm_error:
                    print(f"No se pudo enviar mensaje privado al usuario: {dm_error}")

                update_grupo_tutoria(grupo[GRUPO_ID], GRUPO_EN_USO=False)
                
        except Exception as e:
            print(f"❌ ERROR PROCESANDO CHAT_MEMBER: {e}")
            import traceback
            traceback.print_exc()