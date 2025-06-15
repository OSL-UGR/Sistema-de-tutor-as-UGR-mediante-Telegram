import sqlite3
import os
from pathlib import Path

# Ruta de la nueva base de datos
DB_PATH = Path(__file__).parent.parent / "tutoria_ugr.db"

def get_db_connection():
    """Obtiene una conexión a la base de datos"""

    return sqlite3.connect(str(DB_PATH))

def create_database():
    """Crea la estructura completa de la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.executescript('''
    -- Tabla de Usuarios
    CREATE TABLE IF NOT EXISTS Usuarios (
        Id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
        Nombre TEXT NOT NULL,
        Apellidos TEXT,
        DNI TEXT,
        Tipo TEXT CHECK(Tipo IN ('estudiante', 'profesor')), 
        Email_UGR TEXT UNIQUE,
        TelegramID INTEGER UNIQUE,
        Registrado TEXT DEFAULT 'NO',
        Area TEXT,       -- Incluir área directamente
        Carrera TEXT,    -- Incluir carrera directamente
        Horario TEXT     -- Añadida columna Horario para compatibilidad
    );
    
    -- Tabla de Carreras
    CREATE TABLE IF NOT EXISTS Carreras (
        id_carrera INTEGER PRIMARY KEY AUTOINCREMENT,
        Nombre_carrera TEXT NOT NULL UNIQUE
    );
    
    -- Tabla de Asignaturas
    CREATE TABLE IF NOT EXISTS Asignaturas (
        Id_asignatura INTEGER PRIMARY KEY AUTOINCREMENT,
        Nombre TEXT NOT NULL,
        Codigo_Asignatura TEXT UNIQUE,
        Id_carrera INTEGER,
        FOREIGN KEY (Id_carrera) REFERENCES Carreras(id_carrera)
    );
    
    -- Tabla de Matrículas (con campo Tipo sin valor predeterminado)
    CREATE TABLE IF NOT EXISTS Matriculas (
        id_matricula INTEGER PRIMARY KEY AUTOINCREMENT,
        Id_usuario INTEGER,
        Id_asignatura INTEGER,
        Curso TEXT,
        Tipo TEXT,  -- Campo Tipo sin valor predeterminado
        FOREIGN KEY (Id_usuario) REFERENCES Usuarios(Id_usuario),
        FOREIGN KEY (Id_asignatura) REFERENCES Asignaturas(Id_asignatura)
    );
    
    -- Tabla de Grupos de Tutoría
    CREATE TABLE IF NOT EXISTS Grupos_tutoria (
        id_sala INTEGER PRIMARY KEY AUTOINCREMENT,
        Id_usuario INTEGER NOT NULL,
        Nombre_sala TEXT NOT NULL,
        Tipo_sala TEXT NOT NULL CHECK(Tipo_sala IN ('privada', 'pública')),
        Id_asignatura INTEGER,
        Chat_id TEXT UNIQUE,
        Enlace_invitacion TEXT,
        Proposito_sala TEXT,
        Fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (Id_usuario) REFERENCES Usuarios(Id_usuario),
        FOREIGN KEY (Id_asignatura) REFERENCES Asignaturas(Id_asignatura)
    );
    
    -- Tabla para miembros de grupos
    CREATE TABLE IF NOT EXISTS Miembros_Grupo (
        id_miembro INTEGER PRIMARY KEY AUTOINCREMENT,
        id_sala INTEGER,
        Id_usuario INTEGER,
        Fecha_union TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        Estado TEXT DEFAULT 'activo',
        FOREIGN KEY (id_sala) REFERENCES Grupos_tutoria(id_sala),
        FOREIGN KEY (Id_usuario) REFERENCES Usuarios(Id_usuario),
        UNIQUE(id_sala, Id_usuario)
    );
    
    -- Tabla de Valoraciones
    CREATE TABLE IF NOT EXISTS Valoraciones (
        id_valoracion INTEGER PRIMARY KEY AUTOINCREMENT,
        evaluador_id INTEGER,
        profesor_id INTEGER,
        puntuacion INTEGER CHECK(puntuacion BETWEEN 1 AND 5),
        comentario TEXT,
        fecha TEXT,
        es_anonimo INTEGER DEFAULT 0,
        id_sala INTEGER,
        FOREIGN KEY (evaluador_id) REFERENCES Usuarios(Id_usuario),
        FOREIGN KEY (profesor_id) REFERENCES Usuarios(Id_usuario)
    );
    
    -- Tabla de Horarios mejorada
    CREATE TABLE IF NOT EXISTS Horarios_Profesores (
        id_horario INTEGER PRIMARY KEY AUTOINCREMENT,
        Id_usuario INTEGER NOT NULL,
        dia TEXT NOT NULL,
        hora_inicio TEXT NOT NULL,
        hora_fin TEXT NOT NULL,
        FOREIGN KEY (Id_usuario) REFERENCES Usuarios(Id_usuario)
    );
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ Base de datos creada exitosamente en: {DB_PATH}")
    print("   Estructura de base de datos lista para cargar datos del Excel")

def actualizar_estructura_tablas():
    """Actualiza la estructura de las tablas existentes según sea necesario"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar y actualizar Grupos_tutoria
    try:
        cursor.execute("SELECT Proposito_sala FROM Grupos_tutoria LIMIT 1")
    except:
        print("Actualizando Grupos_tutoria: añadiendo columna Proposito_sala")
        cursor.execute("ALTER TABLE Grupos_tutoria ADD COLUMN Proposito_sala TEXT")
    
    try:
        cursor.execute("SELECT Fecha_creacion FROM Grupos_tutoria LIMIT 1")
    except:
        print("Actualizando Grupos_tutoria: añadiendo columna Fecha_creacion")
        cursor.execute("ALTER TABLE Grupos_tutoria ADD COLUMN Fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    
    # Verificar y actualizar Valoraciones
    try:
        cursor.execute("SELECT id_sala FROM Valoraciones LIMIT 1")
    except:
        print("Actualizando Valoraciones: añadiendo columna id_sala")
        cursor.execute("ALTER TABLE Valoraciones ADD COLUMN id_sala INTEGER")
    
    conn.commit()
    conn.close()
    print("✅ Estructura de tablas actualizada correctamente")

# Agregar esto al bloque principal para que se ejecute al iniciar
if __name__ == "__main__":
    create_database()
    actualizar_estructura_tablas()