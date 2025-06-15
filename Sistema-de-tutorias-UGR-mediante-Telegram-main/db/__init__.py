import os
import sys
from pathlib import Path

# Añadir directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar configuración
try:
    from config import DB_PATH
except ImportError:
    # Si no podemos importar config, definimos DB_PATH directamente
    DB_PATH = Path(__file__).parent.parent / "tutoria_ugr.db"

def init_db():
    """Inicializa la base de datos si no existe"""
    if not os.path.exists(DB_PATH):
        from .models import create_database
        create_database()
        print(f"✅ Base de datos creada en: {DB_PATH}")
    else:
        print(f"✅ Base de datos encontrada en: {DB_PATH}")