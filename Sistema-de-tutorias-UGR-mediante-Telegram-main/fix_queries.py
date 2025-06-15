import os
import re
import sqlite3
from pathlib import Path

# Ruta de la base de datos
DB_PATH = Path(__file__).parent / "tutoria_ugr.db"

def find_problematic_queries():
    """Busca consultas SQL problemáticas en archivos Python"""
    problematic_files = []
    
    # Directorios a buscar
    dirs_to_search = [".", "handlers", "db", "utils"]
    
    print("\n🔍 Buscando consultas SQL con referencia a hp.Horario...")
    
    for directory in dirs_to_search:
        dir_path = Path(__file__).parent / directory
        if dir_path.exists():
            for file_path in dir_path.glob("*.py"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Buscar consultas SQL que contengan hp.Horario
                    if "hp.Horario" in content or "Horarios_Profesores" in content:
                        problematic_files.append((file_path, content))
                        print(f"  - Encontrado en: {file_path}")
    
    return problematic_files

def fix_db_queries():
    """Intenta arreglar la consulta problemática en db/queries.py"""
    query_file = Path(__file__).parent / "db" / "queries.py"
    
    if not query_file.exists():
        print(f"❌ No se encuentra el archivo {query_file}")
        return False
    
    with open(query_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Expresión regular para encontrar consultas SQL que usen hp.Horario
    pattern = r'(SELECT\s+[^;]*\bhp\.Horario\b[^;]*FROM)'
    
    if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
        # Reemplazar hp.Horario por la información formateada de día y hora
        modified = re.sub(
            pattern, 
            r'\1 hp.dia || \' de \' || hp.hora_inicio || \' a \' || hp.hora_fin AS Horario FROM',
            content, 
            flags=re.IGNORECASE | re.DOTALL
        )
        
        with open(query_file, 'w', encoding='utf-8') as f:
            f.write(modified)
        
        print(f"✅ Archivo {query_file} actualizado")
        return True
    
    print("⚠️ No se encontró ninguna consulta que use hp.Horario")
    return False

def add_get_horarios_profesor():
    """Añade una función get_horarios_profesor a queries.py"""
    query_file = Path(__file__).parent / "db" / "queries.py"
    
    if not query_file.exists():
        print(f"❌ No se encuentra el archivo {query_file}")
        return False
    
    with open(query_file, 'a', encoding='utf-8') as f:
        f.write("""
def get_horarios_profesor(profesor_id):
    '''Obtiene los horarios de un profesor específico'''
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            hp.id_horario,
            hp.dia,
            hp.hora_inicio,
            hp.hora_fin,
            hp.dia || ' de ' || hp.hora_inicio || ' a ' || hp.hora_fin AS horario_formateado
        FROM 
            Horarios_Profesores hp
        WHERE 
            hp.Id_usuario = ?
        ORDER BY 
            CASE 
                WHEN hp.dia = 'Lunes' THEN 1
                WHEN hp.dia = 'Martes' THEN 2
                WHEN hp.dia = 'Miércoles' THEN 3
                WHEN hp.dia = 'Jueves' THEN 4
                WHEN hp.dia = 'Viernes' THEN 5
                ELSE 6
            END,
            hp.hora_inicio
    ''', (profesor_id,))
    
    horarios = cursor.fetchall()
    conn.close()
    
    # Convertir a lista de diccionarios
    return [dict(zip(['id_horario', 'dia', 'hora_inicio', 'hora_fin', 'horario_formateado'], h)) for h in horarios]
""")
    
    print(f"✅ Función get_horarios_profesor añadida a {query_file}")
    return True

if __name__ == "__main__":
    print("\n==== DIAGNÓSTICO Y CORRECCIÓN DE CONSULTAS SQL ====")
    
    # 1. Buscar archivos problemáticos
    problematic_files = find_problematic_queries()
    
    # 2. Intentar arreglar consultas
    if problematic_files:
        fixed = fix_db_queries()
        if fixed:
            print("\n✅ Consultas SQL actualizadas")
        else:
            print("\n⚠️ Se encontraron archivos problemáticos pero no se pudieron corregir automáticamente")
            print("Revise manualmente los archivos mencionados arriba")
    else:
        print("\nNo se encontraron consultas problemáticas")
    
    # 3. Añadir función de horarios
    add_get_horarios_profesor()
    
    print("\n🔄 Corrección completada. Intente ejecutar el bot nuevamente.")