import os
import sys
import sqlite3

# Importar la configuración para acceder a las mismas rutas
from config import DB_PATH

def obtener_conexion():
    """Conecta a la base de datos y devuelve la conexión"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def listar_salas(id_usuario=None):
    """Lista todas las salas o solo las de un profesor específico"""
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    if id_usuario:
        cursor.execute("""
            SELECT g.id_sala, g.Nombre_sala, g.Chat_id, g.Proposito_sala, g.Tipo_sala, 
                   u.Nombre as NombreProfesor, a.Nombre as NombreAsignatura,
                   (SELECT COUNT(*) FROM Miembros_Grupo mg WHERE mg.id_sala = g.id_sala) as TotalMiembros
            FROM Grupos_tutoria g
            JOIN Usuarios u ON g.Id_usuario = u.Id_usuario
            LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
            WHERE g.Id_usuario = ?
            ORDER BY g.Fecha_creacion DESC
        """, (id_usuario,))
    else:
        cursor.execute("""
            SELECT g.id_sala, g.Nombre_sala, g.Chat_id, g.Proposito_sala, g.Tipo_sala, 
                   u.Nombre as NombreProfesor, a.Nombre as NombreAsignatura,
                   (SELECT COUNT(*) FROM Miembros_Grupo mg WHERE mg.id_sala = g.id_sala) as TotalMiembros
            FROM Grupos_tutoria g
            JOIN Usuarios u ON g.Id_usuario = u.Id_usuario
            LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
            ORDER BY g.Fecha_creacion DESC
        """)
    
    salas = cursor.fetchall()
    conn.close()
    return salas

def eliminar_sala_prueba(id_sala, id_usuario=None):
    """Intenta eliminar una sala paso a paso, mostrando diagnóstico en cada etapa"""
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    print(f"\n🔍 DIAGNÓSTICO DE ELIMINACIÓN DE SALA ID: {id_sala}")
    print("=" * 50)
    
    # PASO 1: Verificar si la sala existe
    try:
        if id_usuario:
            cursor.execute(
                "SELECT * FROM Grupos_tutoria WHERE id_sala = ? AND Id_usuario = ?", 
                (id_sala, id_usuario)
            )
        else:
            cursor.execute("SELECT * FROM Grupos_tutoria WHERE id_sala = ?", (id_sala,))
        
        sala = cursor.fetchone()
        
        if sala:
            print(f"✅ PASO 1: Sala encontrada correctamente")
            print(f"   Nombre: {sala['Nombre_sala']}")
            print(f"   Chat ID Telegram: {sala['Chat_id']}")
            print(f"   Propósito: {sala['Proposito_sala']}")
        else:
            print(f"❌ PASO 1: Sala no encontrada. Verifica el ID {id_sala}")
            if id_usuario:
                print(f"   Nota: Estás buscando solo salas donde el usuario {id_usuario} es propietario")
            return False
    except Exception as e:
        print(f"❌ PASO 1: Error al verificar la sala: {e}")
        conn.close()
        return False
    
    # PASO 2: Verificar miembros de la sala
    try:
        cursor.execute(
            "SELECT COUNT(*) as total FROM Miembros_Grupo WHERE id_sala = ?", 
            (id_sala,)
        )
        miembros = cursor.fetchone()
        print(f"✅ PASO 2: Verificación de miembros completada")
        print(f"   Total miembros: {miembros['total']}")
    except Exception as e:
        print(f"❌ PASO 2: Error al verificar miembros: {e}")
        conn.close()
        return False
    
    # PASO 3: Intentar eliminar miembros (sin commit)
    try:
        cursor.execute("DELETE FROM Miembros_Grupo WHERE id_sala = ?", (id_sala,))
        print(f"✅ PASO 3: Consulta de eliminación de miembros ejecutada")
        print(f"   Filas afectadas: {cursor.rowcount}")
    except Exception as e:
        print(f"❌ PASO 3: Error al eliminar miembros: {e}")
        conn.close()
        return False
    
    # PASO 4: Intentar eliminar la sala (sin commit)
    try:
        if id_usuario:
            cursor.execute(
                "DELETE FROM Grupos_tutoria WHERE id_sala = ? AND Id_usuario = ?", 
                (id_sala, id_usuario)
            )
        else:
            cursor.execute("DELETE FROM Grupos_tutoria WHERE id_sala = ?", (id_sala,))
        
        print(f"✅ PASO 4: Consulta de eliminación de sala ejecutada")
        print(f"   Filas afectadas: {cursor.rowcount}")
        
        if cursor.rowcount == 0:
            print(f"⚠️ ADVERTENCIA: No se eliminó ninguna fila. Posibles causas:")
            print(f"   - El ID de sala no existe")
            print(f"   - El usuario especificado no es propietario de la sala")
            print(f"   - Hay restricciones de clave foránea que impiden la eliminación")
    except Exception as e:
        print(f"❌ PASO 4: Error al eliminar sala: {e}")
        conn.close()
        return False
    
    # PASO 5: Verificar referencias en otras tablas
    try:
        # Verificar posibles tablas que referencian a Grupos_tutoria
        tablas_relacionadas = [
            "Miembros_Grupo", 
            # ... añade otras tablas que puedan tener relación con Grupos_tutoria
        ]
        
        for tabla in tablas_relacionadas:
            cursor.execute(f"SELECT COUNT(*) as total FROM {tabla} WHERE id_sala = ?", (id_sala,))
            refs = cursor.fetchone()
            if refs and refs['total'] > 0:
                print(f"⚠️ ADVERTENCIA: Existen {refs['total']} referencias en tabla {tabla}")
    except Exception as e:
        print(f"⚠️ PASO 5: Error al verificar referencias: {e}")
    
    # Revertir cambios para este test
    conn.rollback()
    print("\n✅ Diagnóstico completado (cambios no aplicados)")
    print("Para eliminar realmente la sala, ejecuta eliminar_sala_confirmado()")
    
    conn.close()
    return True

def eliminar_sala_confirmado(id_sala, id_usuario=None):
    """Elimina definitivamente la sala después del diagnóstico"""
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    try:
        # Guardar información de la sala antes de eliminarla
        if id_usuario:
            cursor.execute(
                "SELECT Nombre_sala FROM Grupos_tutoria WHERE id_sala = ? AND Id_usuario = ?", 
                (id_sala, id_usuario)
            )
        else:
            cursor.execute("SELECT Nombre_sala FROM Grupos_tutoria WHERE Chat_id = ? OR id_sala = ?", 
                           (id_sala, id_sala))
        
        sala = cursor.fetchone()
        
        if not sala:
            print(f"❌ No se encontró la sala con ID {id_sala}")
            conn.close()
            return False
        
        nombre_sala = sala['Nombre_sala']
        
        # Primero eliminar miembros
        cursor.execute("DELETE FROM Miembros_Grupo WHERE id_sala = ?", (id_sala,))
        miembros_eliminados = cursor.rowcount
        
        # Luego eliminar la sala
        if id_usuario:
            cursor.execute(
                "DELETE FROM Grupos_tutoria WHERE id_sala = ? AND Id_usuario = ?", 
                (id_sala, id_usuario)
            )
        else:
            cursor.execute("DELETE FROM Grupos_tutoria WHERE Chat_id = ? OR id_sala = ?", 
                           (id_sala, id_sala))
        
        salas_eliminadas = cursor.rowcount
        
        # Confirmar los cambios
        conn.commit()
        
        print(f"✅ Sala '{nombre_sala}' eliminada correctamente")
        print(f"   Miembros eliminados: {miembros_eliminados}")
        print(f"   Salas eliminadas: {salas_eliminadas}")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error al eliminar sala: {e}")
        return False
    finally:
        conn.close()

def verificar_estructura_bd():
    """Verifica la estructura de las tablas relacionadas con salas"""
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    print("\n🔍 VERIFICACIÓN DE ESTRUCTURA DE BASE DE DATOS")
    print("=" * 50)
    
    # Verificar estructura de Grupos_tutoria
    try:
        cursor.execute("PRAGMA table_info(Grupos_tutoria)")
        columnas = cursor.fetchall()
        
        print("Tabla Grupos_tutoria:")
        for col in columnas:
            print(f"  - {col['name']} ({col['type']})")
        
        # Verificar claves primarias
        cursor.execute("PRAGMA index_list(Grupos_tutoria)")
        indices = cursor.fetchall()
        
        for idx in indices:
            if idx['origin'] == 'pk':
                cursor.execute(f"PRAGMA index_info({idx['name']})")
                pk_info = cursor.fetchall()
                pk_cols = [info['name'] for info in pk_info]
                print(f"\nClave primaria: {', '.join(pk_cols)}")
    except Exception as e:
        print(f"❌ Error al verificar estructura de Grupos_tutoria: {e}")
    
    # Verificar estructura de Miembros_Grupo
    try:
        print("\nTabla Miembros_Grupo:")
        cursor.execute("PRAGMA table_info(Miembros_Grupo)")
        columnas = cursor.fetchall()
        
        for col in columnas:
            print(f"  - {col['name']} ({col['type']})")
    except Exception as e:
        print(f"❌ Error al verificar estructura de Miembros_Grupo: {e}")
    
    # Verificar restricciones de clave foránea
    try:
        print("\nRestricciones de clave foránea:")
        cursor.execute("PRAGMA foreign_key_list(Miembros_Grupo)")
        fks = cursor.fetchall()
        
        for fk in fks:
            print(f"  - Columna: {fk['from']} -> {fk['table']}.{fk['to']}")
            print(f"    Acciones: ON UPDATE: {fk['on_update']}, ON DELETE: {fk['on_delete']}")
    except Exception as e:
        print(f"❌ Error al verificar claves foráneas: {e}")
    
    conn.close()

def obtener_usuario_por_telegram(telegram_id):
    """Obtiene información del usuario por su ID de Telegram"""
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM Usuarios WHERE TelegramID = ?", 
        (telegram_id,)
    )
    user = cursor.fetchone()
    conn.close()
    
    return user if user else None

def main():
    """Función principal del script de diagnóstico"""
    print("🔧 HERRAMIENTA DE DIAGNÓSTICO DE SALAS DE TUTORÍA")
    print("=" * 50)
    print("\nEste script diagnostica problemas con la eliminación de salas.\n")
    
    # Verificar que la base de datos existe
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Base de datos no encontrada en {DB_PATH}")
        return
    
    print(f"✅ Base de datos encontrada: {DB_PATH}")
    
    while True:
        print("\n" + "=" * 50)
        print("OPCIONES DISPONIBLES:")
        print("1. Listar todas las salas de tutoría")
        print("2. Listar mis salas de tutoría (requiere ID de Telegram)")
        print("3. Diagnosticar eliminación de una sala")
        print("4. Eliminar una sala definitivamente")
        print("5. Verificar estructura de la base de datos")
        print("0. Salir")
        
        opcion = input("\nSelecciona una opción: ")
        
        if opcion == "1":
            salas = listar_salas()
            print("\n📋 LISTADO DE TODAS LAS SALAS:")
            print("=" * 50)
            
            if not salas:
                print("No hay salas registradas en la base de datos.")
            else:
                for sala in salas:
                    print(f"ID: {sala['id_sala']} - {sala['Nombre_sala']}")
                    print(f"  Profesor: {sala['NombreProfesor']}")
                    print(f"  Asignatura: {sala['NombreAsignatura'] or 'General'}")
                    print(f"  Propósito: {sala['Proposito_sala'] or 'No definido'}")
                    print(f"  Miembros: {sala['TotalMiembros']}")
                    print(f"  Chat ID Telegram: {sala['Chat_id']}")
                    print("-" * 40)
        
        elif opcion == "2":
            telegram_id = input("Introduce tu ID de Telegram: ")
            
            try:
                telegram_id = int(telegram_id)
                user = obtener_usuario_por_telegram(telegram_id)
                
                if not user:
                    print(f"❌ No se encontró ningún usuario con ID de Telegram {telegram_id}")
                    continue
                
                if user['Tipo'] != 'profesor':
                    print(f"❌ El usuario {user['Nombre']} no es profesor")
                    continue
                
                print(f"\n👤 Usuario: {user['Nombre']} {user['Apellidos'] or ''}")
                print(f"   Email: {user['Email_UGR']}")
                
                salas = listar_salas(user['Id_usuario'])
                
                print("\n📋 TUS SALAS DE TUTORÍA:")
                print("=" * 50)
                
                if not salas:
                    print("No has creado ninguna sala de tutoría.")
                else:
                    for sala in salas:
                        print(f"ID: {sala['id_sala']} - {sala['Nombre_sala']}")
                        print(f"  Asignatura: {sala['NombreAsignatura'] or 'General'}")
                        print(f"  Propósito: {sala['Proposito_sala'] or 'No definido'}")
                        print(f"  Miembros: {sala['TotalMiembros']}")
                        print(f"  Chat ID Telegram: {sala['Chat_id']}")
                        print("-" * 40)
            except ValueError:
                print("❌ El ID de Telegram debe ser un número")
        
        elif opcion == "3":
            try:
                sala_id = int(input("Introduce el ID de la sala a diagnosticar: "))
                usar_usuario = input("¿Filtrar por propietario? (s/n): ").lower() == 's'
                
                if usar_usuario:
                    telegram_id = int(input("Introduce el ID de Telegram del propietario: "))
                    user = obtener_usuario_por_telegram(telegram_id)
                    
                    if not user:
                        print(f"❌ No se encontró ningún usuario con ID de Telegram {telegram_id}")
                        continue
                    
                    eliminar_sala_prueba(sala_id, user['Id_usuario'])
                else:
                    eliminar_sala_prueba(sala_id)
            except ValueError:
                print("❌ Los IDs deben ser números")
        
        elif opcion == "4":
            try:
                sala_id = int(input("Introduce el ID de la sala a eliminar: "))
                usar_usuario = input("¿Filtrar por propietario? (s/n): ").lower() == 's'
                
                if usar_usuario:
                    telegram_id = int(input("Introduce el ID de Telegram del propietario: "))
                    user = obtener_usuario_por_telegram(telegram_id)
                    
                    if not user:
                        print(f"❌ No se encontró ningún usuario con ID de Telegram {telegram_id}")
                        continue
                    
                    confirmar = input(f"⚠️ ¿SEGURO que quieres ELIMINAR la sala {sala_id}? (s/n): ").lower()
                    if confirmar == 's':
                        eliminar_sala_confirmado(sala_id, user['Id_usuario'])
                else:
                    confirmar = input(f"⚠️ ¿SEGURO que quieres ELIMINAR la sala {sala_id}? (s/n): ").lower()
                    if confirmar == 's':
                        eliminar_sala_confirmado(sala_id)
            except ValueError:
                print("❌ Los IDs deben ser números")
        
        elif opcion == "5":
            verificar_estructura_bd()
        
        elif opcion == "0":
            print("\n👋 ¡Hasta pronto!")
            break
        
        else:
            print("❌ Opción no válida")

if __name__ == "__main__":
    main()