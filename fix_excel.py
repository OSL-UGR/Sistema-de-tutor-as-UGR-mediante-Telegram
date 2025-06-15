import os
import pandas as pd
from pathlib import Path
import sys

def diagnosticar_excel():
    """Diagnostica problemas con el archivo Excel"""
    # Verificar directorio data
    data_dir = Path(__file__).parent / "data"
    excel_path = data_dir / "usuarios.xlsx"
    
    print("\n==== DIAGNÓSTICO DEL EXCEL ====")
    
    # Verificar si existe el directorio data
    if not os.path.exists(data_dir):
        print("❌ ERROR: No existe el directorio 'data'")
        print("   Creando directorio...")
        os.makedirs(data_dir)
        print("✅ Directorio 'data' creado")
    else:
        print("✅ Directorio 'data' encontrado")
    
    # Verificar si existe el archivo Excel
    if not os.path.exists(excel_path):
        print("❌ ERROR: No existe el archivo 'usuarios.xlsx'")
        print("   Creando archivo de ejemplo...")
        
        # Crear DataFrame de ejemplo
        data = {
            'Nombre': ['Alberto', 'María', 'Juan', 'Pablo'],
            'Apellidos': ['Velasco Fuentes', 'López Martínez', 'García Ruiz', 'Romero Gil'],
            'DNI': ['78224259', '12345678A', '23456789B', '34567890C'],
            'Email': ['alb172@correo.ugr.es', 'maria@correo.ugr.es', 'juan@correo.ugr.es', 'pablo@ugr.es'],
            'Tipo': ['estudiante', 'estudiante', 'estudiante', 'profesor'],
            'Area': ['Ingeniería', 'Ciencias', 'Ciencias', 'Ingeniería'],
            'Carrera': ['Ingeniería de Software', 'Matemáticas', 'Física', 'Ingeniería de Software'],
            'Asignaturas': ['ST;SRC;RIM', 'Algebra;Cálculo', 'Física Cuántica', 'ST;SRC'],
            'Horario': ['', '', '', 'Lunes y Miércoles 10:00-12:00']
        }
        
        df = pd.DataFrame(data)
        df.to_excel(excel_path, index=False)
        print(f"✅ Archivo Excel de ejemplo creado en {excel_path}")
    else:
        print("✅ Archivo Excel encontrado")
        
        # Verificar estructura del Excel
        try:
            df = pd.read_excel(excel_path)
            print(f"   Columnas encontradas: {df.columns.tolist()}")
            print(f"   Número de registros: {len(df)}")
            
            # Verificar columnas requeridas
            columnas_requeridas = ['Nombre', 'Apellidos', 'DNI', 'Email', 'Tipo', 'Area', 'Carrera', 'Asignaturas']
            faltantes = [col for col in columnas_requeridas if col not in df.columns]
            
            if faltantes:
                print(f"❌ ERROR: Faltan columnas requeridas: {', '.join(faltantes)}")
            else:
                print("✅ El Excel tiene todas las columnas requeridas")
            
            # Verificar formato de emails
            emails_invalidos = []
            for i, email in enumerate(df['Email']):
                if not isinstance(email, str) or not ('@ugr.es' in email or '@correo.ugr.es' in email):
                    emails_invalidos.append(f"Fila {i+2}: {email}")
            
            if emails_invalidos:
                print("❌ ERROR: Hay emails con formato incorrecto:")
                for email in emails_invalidos[:3]:  # Mostrar solo los primeros 3
                    print(f"   - {email}")
                if len(emails_invalidos) > 3:
                    print(f"   - Y {len(emails_invalidos) - 3} más...")
            else:
                print("✅ Todos los emails tienen formato correcto")
            
            # Verificar separación de asignaturas
            filas_con_comas = []
            for i, asig in enumerate(df['Asignaturas']):
                if isinstance(asig, str) and ',' in asig and ';' not in asig:
                    filas_con_comas.append(f"Fila {i+2}: {asig}")
            
            if filas_con_comas:
                print("⚠️ ADVERTENCIA: Hay asignaturas separadas por comas en lugar de punto y coma:")
                for fila in filas_con_comas[:3]:
                    print(f"   - {fila}")
                if len(filas_con_comas) > 3:
                    print(f"   - Y {len(filas_con_comas) - 3} más...")
            else:
                print("✅ El formato de separación de asignaturas es correcto")
                
        except Exception as e:
            print(f"❌ ERROR al leer el Excel: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--crear_nuevo":
        # Forzar creación de nuevo archivo
        data_dir = Path(__file__).parent / "data"
        excel_path = data_dir / "usuarios.xlsx"
        if os.path.exists(excel_path):
            os.remove(excel_path)
            print("Archivo Excel anterior eliminado")
    diagnosticar_excel()