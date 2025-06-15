import os
import pandas as pd
from pathlib import Path

def reparar_excel():
    """Repara el archivo Excel existente añadiendo los encabezados correctos"""
    data_dir = Path(__file__).parent / "data"
    excel_path = data_dir / "usuarios.xlsx"
    
    print("\n==== REPARACIÓN DEL EXCEL ====")
    
    if os.path.exists(excel_path):
        try:
            # Leer el excel sin encabezados
            df = pd.read_excel(excel_path, header=None)
            print(f"Lectura exitosa. Encontradas {len(df)} filas y {len(df.columns)} columnas.")
            
            # Definir nombres de columnas correctos
            columnas_correctas = ['Nombre', 'Apellidos', 'DNI', 'Email', 'Tipo', 'Area', 'Carrera', 'Asignaturas', 'Horario']
            
            # Si hay más columnas que nombres, ajustar
            if len(df.columns) > len(columnas_correctas):
                print(f"NOTA: El Excel tiene {len(df.columns)} columnas pero solo necesitamos {len(columnas_correctas)}.")
                # Usar solo las primeras columnas que necesitamos
                df = df.iloc[:, :len(columnas_correctas)]
            
            # Si hay menos columnas, añadir columnas vacías
            while len(df.columns) < len(columnas_correctas):
                df[f"Col_{len(df.columns)}"] = ""
                print(f"Añadida columna faltante {len(df.columns)}")
            
            # Asignar nombres correctos
            df.columns = columnas_correctas[:len(df.columns)]
            
            # Si la primera fila parece contener encabezados, eliminarla
            if isinstance(df['Nombre'].iloc[0], str) and df['Nombre'].iloc[0].lower() in ['nombre', 'name', 'nombres']:
                print("Eliminando primera fila que contiene encabezados...")
                df = df.iloc[1:].reset_index(drop=True)
            
            # Guardar el Excel reparado
            backup_path = excel_path.with_suffix('.backup.xlsx')
            if os.path.exists(excel_path):
                import shutil
                shutil.copy(excel_path, backup_path)
                print(f"Backup creado en {backup_path}")
            
            df.to_excel(excel_path, index=False)
            print(f"✅ Excel reparado y guardado en {excel_path}")
            
            return True
        except Exception as e:
            print(f"❌ ERROR al reparar el Excel: {e}")
            return False
    else:
        print("❌ No se encontró el archivo Excel para reparar.")
        return False

if __name__ == "__main__":
    reparar_excel()