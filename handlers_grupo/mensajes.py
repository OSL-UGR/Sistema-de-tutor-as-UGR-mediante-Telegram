import datetime
import os
import sys

from handlers_grupo.tutorias import COMMAND_FINALIZAR
from handlers_grupo.utils import configurar_logger
from utils.state_manager import *
from db.queries import delete_reaccion, get_grupos_tutoria, get_mensajes, get_reacciones, get_usuarios_local, insert_mensaje, insert_reaccion, update_reaccion
from db.constantes import *

# Configuración de ruta para importar correctamente
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar logging
logger = configurar_logger()

def register_handlers(bot):
    @bot.message_handler(func=lambda msg: msg.chat.type in ["group", "supergroup"] and not msg.text.startswith('/'))
    def handle_group_message(message):
        try:
            telegram_id = message.message_id
            chat_id = message.chat.id
            sender_id = message.from_user.id

            grupo = get_grupos_tutoria(GRUPO_ID_CHAT=chat_id)

            if grupo:
                grupo = grupo[0]
                profesor_id = grupo[GRUPO_ID_PROFESOR]
                asignatura_id = grupo[GRUPO_ID_ASIGNATURA]
                sender = get_usuarios_local(USUARIO_ID_TELEGRAM=sender_id)
                
                if sender:
                    sender = sender[0][USUARIO_ID]
                else:
                    sender = None

                insert_mensaje(
                    telegram_id=telegram_id,
                    chat_id=chat_id,
                    sender_id=sender,
                    profesor_id=profesor_id,
                    asignatura_id=asignatura_id,
                    texto=message.text
                )
                print(f"Guardado mensaje {telegram_id} de usuario {sender_id} en chat {chat_id}")

        except Exception as e:
            print(f"Error al guardar mensaje: {e}")


    @bot.message_reaction_handler()
    def handle_reaction(update):
        """Procesa reacciones añadidas o eliminadas en mensajes"""
        try:    
            chat_id = update.chat.id
            user = update.user
            msg_id = update.message_id
    
            added_reactions = update.new_reaction or []
            removed_reactions = update.old_reaction or []

            mensaje = get_mensajes(MENSAJE_ID_CHAT=chat_id, MENSAJE_ID_TELEGRAM=msg_id)
            profesor = get_usuarios_local(USUARIO_ID_TELEGRAM=user.id)

            if profesor and mensaje and profesor[0][USUARIO_TIPO]==USUARIO_TIPO_PROFESOR:
                profesor = profesor[0]
                mensaje = mensaje[0]
                
                print(f"\n🔁 CAMBIO DE REACCIÓN EN MENSAJE {msg_id} DEL CHAT {chat_id}")
                print(f"👤 Usuario: {user.first_name} (ID: {user.id})")

                if added_reactions:
                    for r in added_reactions:
                        if hasattr(r, 'emoji'):
                            actual = get_reacciones(REACCION_ID_PROFESOR=profesor[USUARIO_ID], REACCION_ID_ALUMNO=mensaje[MENSAJE_ID_SENDER], REACCION_ID_ASIGNATURA=mensaje[MENSAJE_ID_ASIGNATURA], REACCION_EMOJI=r.emoji)
                            if actual:
                                actual = actual[0]
                                update_reaccion(actual[REACCION_ID], REACCION_CANTIDAD=actual[REACCION_CANTIDAD]+1)
                                print(f"➕ Reacción añadida: {r.emoji}")
                            else:
                                insert_reaccion(profesor[USUARIO_ID], mensaje[MENSAJE_ID_SENDER], mensaje[MENSAJE_ID_ASIGNATURA], r.emoji, 1)
                                print(f"➕ Reacción nueva añadida: {r.emoji}")

                if removed_reactions:
                    for r in removed_reactions:
                        if hasattr(r, 'emoji'):
                            print(mensaje[MENSAJE_ID_ASIGNATURA], r.emoji)
                            actual = get_reacciones(REACCION_ID_PROFESOR=profesor[USUARIO_ID], REACCION_ID_ALUMNO=mensaje[MENSAJE_ID_SENDER], REACCION_ID_ASIGNATURA=mensaje[MENSAJE_ID_ASIGNATURA], REACCION_EMOJI=r.emoji)
                            if actual:
                                actual = actual[0]
                                if actual[REACCION_CANTIDAD] > 1:
                                    update_reaccion(actual[REACCION_ID], REACCION_CANTIDAD=actual[REACCION_CANTIDAD]-1)
                                    print(f"➖ Reacción eliminada: {r.emoji}")
                                else:
                                    delete_reaccion(actual[REACCION_ID])
                                    print(f"❌ Reacción eliminada completamente: {r.emoji}")
    
        except Exception as e:
            print(f"❌ ERROR PROCESANDO REACCIÓN: {e}")
            import traceback
            traceback.print_exc()