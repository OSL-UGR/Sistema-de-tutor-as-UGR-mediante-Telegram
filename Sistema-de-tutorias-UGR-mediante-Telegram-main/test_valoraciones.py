import sqlite3
import os
import sys
import time
from datetime import datetime

# Configuración de la base de datos
DB_PATH = os.path.join(os.path.dirname(__file__), 'tutoria_ugr.db')

def get_db_connection():
    """Retorna una conexión a la base de datos"""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def clear_screen():
    """Limpia la pantalla de la terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_telegram_message(sender, message, is_bot=False):
    """Imprime un mensaje simulando la interfaz de Telegram"""
    width = 60
    print("\n" + "-" * width)
    sender_name = "🤖 TutoriaUGR Bot" if is_bot else f"👤 {sender}"
    print(f"{sender_name} - {datetime.now().strftime('%H:%M')}")
    print("-" * width)
    print(f"{message}")
    print("-" * width)

def main_menu():
    """Muestra el menú principal de simulación"""
    clear_screen()
    print("\n===== SIMULADOR DE VALORACIONES DE TUTORÍAS =====\n")
    print("1. Crear valoración de prueba")
    print("2. Ver valoraciones de un profesor")
    print("3. Verificar tabla de valoraciones")
    print("4. Salir")
    
    try:
        option = int(input("\nSelecciona una opción (1-4): "))
        return option
    except ValueError:
        return 0

def select_student():
    """Permite seleccionar cualquier estudiante para la simulación"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Seleccionamos cualquier estudiante sin importar si está en un grupo
    cursor.execute("SELECT Id_usuario, Nombre, Apellidos, Email_UGR FROM Usuarios WHERE Tipo = 'estudiante'")
    estudiantes = cursor.fetchall()
    conn.close()
    
    if not estudiantes:
        print("❌ No hay estudiantes registrados en la base de datos.")
        input("Presiona Enter para continuar...")
        return None
        
    clear_screen()
    print("\n==== SELECCIONA UN ESTUDIANTE PARA LA SIMULACIÓN ====\n")
    
    for i, estudiante in enumerate(estudiantes, 1):
        print(f"{i}. {estudiante['Nombre']} {estudiante['Apellidos'] or ''} - {estudiante['Email_UGR']}")
    
    try:
        seleccion = int(input("\nSelecciona un estudiante (número): "))
        if 1 <= seleccion <= len(estudiantes):
            return estudiantes[seleccion-1]
        else:
            return None
    except ValueError:
        return None

def select_professor():
    """Permite seleccionar cualquier profesor para la simulación"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Seleccionamos cualquier profesor
    cursor.execute("SELECT Id_usuario, Nombre, Apellidos, Email_UGR FROM Usuarios WHERE Tipo = 'profesor'")
    profesores = cursor.fetchall()
    conn.close()
    
    if not profesores:
        print("❌ No hay profesores registrados en la base de datos.")
        input("Presiona Enter para continuar...")
        return None
        
    clear_screen()
    print("\n==== SELECCIONA UN PROFESOR PARA LA SIMULACIÓN ====\n")
    
    for i, profesor in enumerate(profesores, 1):
        print(f"{i}. {profesor['Nombre']} {profesor['Apellidos'] or ''} - {profesor['Email_UGR']}")
    
    try:
        seleccion = int(input("\nSelecciona un profesor (número): "))
        if 1 <= seleccion <= len(profesores):
            return profesores[seleccion-1]
        else:
            return None
    except ValueError:
        return None

def select_group_or_create_fake(profesor_id):
    """Selecciona un grupo existente o crea uno ficticio para pruebas"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar grupos del profesor
    cursor.execute("""
        SELECT id_sala, Nombre_sala FROM Grupos_tutoria 
        WHERE Id_usuario = ?
    """, (profesor_id,))
    grupos = cursor.fetchall()
    
    # Si no hay grupos, SIEMPRE creamos uno temporal para pruebas
    if not grupos:
        # Grupo ficticio garantizado para pruebas
        grupo_ficticio = {
            "id_sala": 99999,  # ID ficticio
            "Nombre_sala": "[TEST] Valoración de Prueba"
        }
        grupos = [grupo_ficticio]
        print("\n⚠️ El profesor no tiene grupos. Usando grupo ficticio para pruebas.")
    
    conn.close()
    
    # Si solo hay un grupo, seleccionarlo automáticamente
    if len(grupos) == 1:
        return grupos[0]
    
    # Si hay múltiples grupos, mostrar opciones
    clear_screen()
    print("\n==== SELECCIONA UN GRUPO PARA LA VALORACIÓN ====\n")
    
    for i, grupo in enumerate(grupos, 1):
        print(f"{i}. {grupo['Nombre_sala']} (ID: {grupo['id_sala']})")
    
    try:
        seleccion = int(input("\nSelecciona un grupo (número): "))
        if 1 <= seleccion <= len(grupos):
            return grupos[seleccion-1]
        else:
            # En lugar de retornar None, usamos un grupo por defecto
            return grupos[0]
    except ValueError:
        return grupos[0]  # Retornar el primer grupo por defecto

def create_test_rating():
    """Crea una valoración de prueba"""
    # 1. Seleccionamos estudiante
    estudiante = select_student()
    if not estudiante:
        print("❌ Operación cancelada: No se seleccionó estudiante.")
        input("Presiona Enter para continuar...")
        return
    
    # 2. Seleccionamos profesor
    profesor = select_professor()
    if not profesor:
        print("❌ Operación cancelada: No se seleccionó profesor.")
        input("Presiona Enter para continuar...")
        return
    
    # 3. Seleccionamos o creamos un grupo (SIEMPRE crear uno ficticio si es necesario)
    grupo = select_group_or_create_fake(profesor['Id_usuario'])
    if not grupo:
        # Si no hay grupos y no se pudo crear uno ficticio, creamos uno básico
        grupo = {
            "id_sala": 99999,  # ID ficticio para pruebas
            "Nombre_sala": "[TEST] Valoración de Prueba"
        }
        print("⚠️ Usando grupo de prueba ficticio para la valoración")
    
    # 4. Seleccionamos puntuación
    clear_screen()
    print_telegram_message("Bot", "🌟 *¿Cómo valorarías esta tutoría?*\n\nSelecciona una puntuación del 1 al 5 estrellas:", True)
    for i in range(1, 6):
        stars = "⭐" * i
        print(f"{i}. {stars}")
    
    try:
        puntuacion = int(input("\nSelecciona una puntuación (1-5): "))
        if not (1 <= puntuacion <= 5):
            print("❌ Puntuación inválida.")
            input("Presiona Enter para continuar...")
            return
    except ValueError:
        print("❌ Entrada inválida.")
        input("Presiona Enter para continuar...")
        return
    
    # 5. Ingresamos un comentario
    clear_screen()
    print_telegram_message("Bot", f"🌟 Has seleccionado: {'⭐' * puntuacion}\n\n¿Quieres añadir un comentario? (opcional)\nEscribe tu comentario o deja en blanco para omitir.", True)
    
    comentario = input("\nComentario (opcional): ").strip()
    if not comentario:
        comentario = None
    
    # 6. Guardamos la valoración en la BD
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar si la tabla existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Valoraciones';")
        if not cursor.fetchone():
            # Crear tabla si no existe
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Valoraciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_sala INTEGER NOT NULL,
                    Id_estudiante INTEGER NOT NULL,
                    Id_profesor INTEGER NOT NULL,
                    puntuacion INTEGER NOT NULL,
                    comentario TEXT,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("\n✅ Tabla Valoraciones creada.")
            
        # Verificar si ya existe una valoración
        cursor.execute("""
            SELECT id FROM Valoraciones 
            WHERE id_sala = ? AND Id_estudiante = ? AND Id_profesor = ?
        """, (grupo['id_sala'], estudiante['Id_usuario'], profesor['Id_usuario']))
        
        existing_rating = cursor.fetchone()
        
        if existing_rating:
            # Primero averiguar el nombre real de la columna ID
            cursor.execute("PRAGMA table_info(Valoraciones);")
            columns = cursor.fetchall()
            id_column_name = None
            
            # Buscar columna que sea PRIMARY KEY
            for col in columns:
                if col['pk'] == 1:  # pk=1 indica PRIMARY KEY
                    id_column_name = col['name']
                    break
            
            if not id_column_name:
                id_column_name = 'id'  # Valor por defecto
                
            # Actualizar valoración existente usando el nombre correcto
            cursor.execute(f"""
                UPDATE Valoraciones 
                SET puntuacion = ?, comentario = ?, fecha = CURRENT_TIMESTAMP
                WHERE {id_column_name} = ?
            """, (puntuacion, comentario, existing_rating[0]))  # Usando [0] para obtener el primer valor
            
            mensaje = f"✅ *Valoración actualizada*\n\n"
        else:
            # Insertar nueva valoración
            cursor.execute("""
                INSERT INTO Valoraciones (id_sala, Id_estudiante, Id_profesor, puntuacion, comentario)
                VALUES (?, ?, ?, ?, ?)
            """, (grupo['id_sala'], estudiante['Id_usuario'], profesor['Id_usuario'], puntuacion, comentario))
            
            mensaje = f"✅ *Nueva valoración registrada*\n\n"
        
        conn.commit()
        
        # 7. Mostrar mensaje de éxito
        mensaje += f"👤 *Estudiante:* {estudiante['Nombre']} {estudiante['Apellidos'] or ''}\n"
        mensaje += f"👨‍🏫 *Profesor:* {profesor['Nombre']} {profesor['Apellidos'] or ''}\n"
        mensaje += f"🏫 *Grupo:* {grupo['Nombre_sala']}\n"
        mensaje += f"⭐ *Valoración:* {'⭐' * puntuacion}\n"
        if comentario:
            mensaje += f"💬 *Comentario:* {comentario}\n"
        
        clear_screen()
        print_telegram_message("Bot", mensaje, True)
        
    except Exception as e:
        print(f"❌ Error al guardar la valoración: {str(e)}")
    
    conn.close()
    input("\nPresiona Enter para continuar...")

def view_professor_ratings():
    """Muestra todas las valoraciones recibidas por un profesor"""
    profesor = select_professor()
    if not profesor:
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar si la tabla existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Valoraciones';")
    if not cursor.fetchone():
        print("❌ La tabla Valoraciones no existe todavía.")
        input("Presiona Enter para continuar...")
        conn.close()
        return
    
    # Obtener valoraciones del profesor
    cursor.execute("""
        SELECT v.*, g.Nombre_sala, e.Nombre as NombreEstudiante, e.Apellidos as ApellidosEstudiante
        FROM Valoraciones v
        LEFT JOIN Grupos_tutoria g ON v.id_sala = g.id_sala
        JOIN Usuarios e ON v.Id_estudiante = e.Id_usuario
        WHERE v.Id_profesor = ?
        ORDER BY v.fecha DESC
    """, (profesor['Id_usuario'],))
    
    valoraciones = cursor.fetchall()
    conn.close()
    
    clear_screen()
    if not valoraciones:
        print_telegram_message("Bot", f"📊 El profesor {profesor['Nombre']} no tiene valoraciones todavía.", True)
        input("\nPresiona Enter para continuar...")
        return
    
    # Calcular estadísticas
    total = len(valoraciones)
    puntuacion_total = sum(v['puntuacion'] for v in valoraciones)
    promedio = puntuacion_total / total
    
    # Crear mensaje
    mensaje = f"📊 *Valoraciones del profesor {profesor['Nombre']} {profesor['Apellidos'] or ''}*\n\n"
    mensaje += f"Valoración media: {promedio:.1f}/5 ({'⭐' * round(promedio)})\n"
    mensaje += f"Total valoraciones: {total}\n\n"
    
    # Mostrar todas las valoraciones
    mensaje += "*Detalle de valoraciones:*\n\n"
    for i, v in enumerate(valoraciones, 1):
        grupo_nombre = v['Nombre_sala'] if v['Nombre_sala'] else f"Grupo ID: {v['id_sala']}"
        mensaje += f"{i}. *{grupo_nombre}*\n"
        mensaje += f"   👤 Estudiante: {v['NombreEstudiante']} {v['ApellidosEstudiante'] or ''}\n"
        mensaje += f"   ⭐ Puntuación: {'⭐' * v['puntuacion']}\n"
        if v['comentario']:
            mensaje += f"   💬 Comentario: _{v['comentario']}_\n"
        mensaje += f"   📅 Fecha: {v['fecha']}\n\n"
    
    print_telegram_message("Bot", mensaje, True)
    input("\nPresiona Enter para continuar...")

def verify_valoraciones_table():
    """Verifica y muestra información sobre la tabla Valoraciones"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    clear_screen()
    print("\n===== VERIFICACIÓN DE LA TABLA VALORACIONES =====\n")
    
    # Verificar si la tabla existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Valoraciones';")
    if not cursor.fetchone():
        print("❌ La tabla Valoraciones NO existe en la base de datos.")
        
        crear = input("\n¿Deseas crear la tabla ahora? (s/n): ")
        if crear.lower() == 's':
            # Crear tabla
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Valoraciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_sala INTEGER NOT NULL,
                    Id_estudiante INTEGER NOT NULL,
                    Id_profesor INTEGER NOT NULL,
                    puntuacion INTEGER NOT NULL,
                    comentario TEXT,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            print("\n✅ Tabla Valoraciones creada correctamente.")
        else:
            conn.close()
            input("\nPresiona Enter para continuar...")
            return
    
    # Mostrar estructura
    cursor.execute("PRAGMA table_info(Valoraciones);")
    columns = cursor.fetchall()
    
    print("✅ Tabla Valoraciones encontrada")
    print("\nEstructura de la tabla:")
    for col in columns:
        print(f"  - {col['name']} ({col['type']})")
    
    # Contar valoraciones
    cursor.execute("SELECT COUNT(*) as total FROM Valoraciones;")
    total = cursor.fetchone()['total']
    
    print(f"\nTotal de valoraciones: {total}")
    
    if total > 0:
        # Ver algunas valoraciones
        cursor.execute("""
            SELECT v.*, 
                   e.Nombre as NombreEstudiante, 
                   p.Nombre as NombreProfesor,
                   g.Nombre_sala
            FROM Valoraciones v
            JOIN Usuarios e ON v.Id_estudiante = e.Id_usuario
            JOIN Usuarios p ON v.Id_profesor = p.Id_usuario
            LEFT JOIN Grupos_tutoria g ON v.id_sala = g.id_sala
            LIMIT 5
        """)
        
        valoraciones = cursor.fetchall()
        
        print("\nÚltimas valoraciones:")
        for v in valoraciones:
            print(f"\n  📝 ID: {v['id']}")
            print(f"  👤 Estudiante: {v['NombreEstudiante']}")
            print(f"  👨‍🏫 Profesor: {v['NombreProfesor']}")
            grupo_nombre = v['Nombre_sala'] if v['Nombre_sala'] else f"Grupo ID: {v['id_sala']}"
            print(f"  🏫 Grupo: {grupo_nombre}")
            print(f"  ⭐ Puntuación: {'⭐' * v['puntuacion']}")
            print(f"  💬 Comentario: {v['comentario'] or '(Sin comentario)'}")
            print(f"  📅 Fecha: {v['fecha']}")
    
    conn.close()
    input("\nPresiona Enter para continuar...")

def main():
    """Función principal del script"""
    while True:
        option = main_menu()
        
        if option == 1:
            create_test_rating()
        elif option == 2:
            view_professor_ratings()
        elif option == 3:
            verify_valoraciones_table()
        elif option == 4:
            print("\nSaliendo del simulador... ¡Hasta pronto!\n")
            sys.exit(0)
        else:
            print("\n❌ Opción inválida. Por favor, intenta de nuevo.")
            time.sleep(1)

if __name__ == "__main__":
    # Verificar que existe la base de datos
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Base de datos no encontrada en {DB_PATH}")
        sys.exit(1)
        
    main()