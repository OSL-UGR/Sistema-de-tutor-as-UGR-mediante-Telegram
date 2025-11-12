"""
main.py — Inicia ambos bots del proyecto (bot_principal y bot_grupos).

Cómo funciona:
- Por defecto intenta arrancar los módulos: "bot_principal" y "bot_grupos".
- Puedes cambiar los módulos a arrancar con la variable de entorno BOT_MODULES, por ejemplo:
  BOT_MODULES="bot_principal,bot_grupos"

El script intenta detectar estas funciones/objetos en cada módulo (en este orden):
- setup_polling()
- main()
- bot.infinity_polling() / bot.polling()

Cada módulo se ejecuta en su propio hilo. Los errores se muestran por consola.
"""

import importlib
import threading
import time
import os
import sys
import traceback

# Módulos por defecto a arrancar (sin sufijo .py)
BOT_MODULES = ["bot_principal","bot_grupos"]


def _run_target(module_name, target_callable):
    try:
        print(f"▶️ Iniciando módulo: {module_name}")
        target_callable()
    except Exception as e:
        print(f"❌ Error en módulo '{module_name}': {e}")
        traceback.print_exc()


def run_module(module_name):
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        print(f"⚠️ No se pudo importar módulo '{module_name}': {e}")
        traceback.print_exc()
        return

    # Priorizar funciones conocidas para iniciar el bot
    if hasattr(mod, "setup_polling") and callable(getattr(mod, "setup_polling")):
        target = lambda: mod.setup_polling()
    elif hasattr(mod, "main") and callable(getattr(mod, "main")):
        target = lambda: mod.main()
    elif hasattr(mod, "bot"):
        bot_obj = getattr(mod, "bot")
        # Telebot tiene polling() o infinity_polling(); preferir infinity_polling
        if hasattr(bot_obj, "infinity_polling") and callable(getattr(bot_obj, "infinity_polling")):
            target = lambda: bot_obj.infinity_polling()
        elif hasattr(bot_obj, "polling") and callable(getattr(bot_obj, "polling")):
            # Llamar a polling con parámetros razonables
            def _polling_wrapper():
                try:
                    bot_obj.remove_webhook()
                except Exception:
                    pass
                bot_obj.polling(none_stop=True)
            target = _polling_wrapper
        else:
            print(f"⚠️ El módulo '{module_name}' expone 'bot' pero no tiene 'infinity_polling' ni 'polling'.")
            return
    else:
        print(f"⚠️ El módulo '{module_name}' no expone 'setup_polling', 'main' ni 'bot'.")
        return

    # Ejecutar en hilo separado para cada módulo
    t = threading.Thread(target=_run_target, args=(module_name, target), name=f"bot-{module_name}")
    t.daemon = True
    t.start()
    return t


def main():
    if not BOT_MODULES:
        print("❗ No hay módulos de bot configurados en BOT_MODULES.")
        sys.exit(1)

    print(f"📥 Módulos a iniciar: {BOT_MODULES}")

    threads = []
    for mod in BOT_MODULES:
        t = run_module(mod)
        if t:
            threads.append(t)

    try:
        # Mantener el proceso vivo; los hilos son daemon, así que la aplicación
        # terminará si el hilo principal recibe SIGINT/SIGTERM.
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("👋 Detenido por usuario (KeyboardInterrupt)")
        # Esperar brevemente a que los hilos terminen su limpieza
        time.sleep(0.5)
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error en main: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
