from pathlib import Path

from db.db import commit, get_cursor

# Ruta de la nueva base de datos
DB_PATH = Path(__file__).parent.parent / "tutoria_ugr.db"

def create_database():
    """Crea la estructura completa de la base de datos"""
    cursor = get_cursor()
    
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
    ''')
    
    commit()
    print(f"✅ Base de datos creada exitosamente en: {DB_PATH}")
    print("   Estructura de base de datos lista para cargar datos del Excel")

# Agregar esto al bloque principal para que se ejecute al iniciar
if __name__ == "__main__":
    create_database()