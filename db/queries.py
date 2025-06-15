import sqlite3
from pathlib import Path
import sys
import os
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# Añadir directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ruta a la base de datos
DB_PATH = Path(__file__).parent.parent / "tutoria_ugr.db"

def get_db_connection():
    """Obtiene una conexión a la base de datos"""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ===== FUNCIONES DE USUARIO =====
def get_user_by_telegram_id(telegram_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Consulta con JOIN para incluir el horario
    cursor.execute("""
        SELECT u.*, hp.dia || ' de ' || hp.hora_inicio || ' a ' || hp.hora_fin AS Horario 
        FROM Usuarios u 
        LEFT JOIN Horarios_Profesores hp ON u.Id_usuario = hp.Id_usuario
        WHERE u.TelegramID = ?
    """, (telegram_id,))
    
    result = cursor.fetchone()
    conn.close()
    return result

def get_user_by_id(user_id):
    """Busca un usuario por su ID en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM Usuarios WHERE Id_usuario = ?", (user_id,))
    user = cursor.fetchone()
    
    conn.close()
    return dict(user) if user else None

def buscar_usuario_por_email(email):
    """Busca un usuario por su email"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM Usuarios WHERE Email_UGR = ?", (email,))
    user = cursor.fetchone()
    
    conn.close()
    return dict(user) if user else None

def create_user(nombre, tipo, email, telegram_id=None, apellidos=None, dni=None, carrera=None, Area=None, registrado="NO"):
    """Crea un nuevo usuario en la base de datos con los datos proporcionados"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """INSERT INTO Usuarios 
            (Nombre, Tipo, Email_UGR, TelegramID, Apellidos, DNI, Carrera, Area, Registrado) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (nombre, tipo, email, telegram_id, apellidos, dni, carrera, Area, registrado)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al crear usuario: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def update_user(user_id, **kwargs):
    """Actualiza los datos de un usuario existente"""
    if not kwargs:
        return False
    
    try:
        # Construir la consulta dinámicamente
        query = "UPDATE Usuarios SET "
        query += ", ".join([f"{key} = ?" for key in kwargs.keys()])
        query += " WHERE Id_usuario = ?"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(query, list(kwargs.values()) + [user_id])
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        import logging
        logging.getLogger('db.queries').error(f"Error al actualizar usuario: {e}")
        return False

def update_horario_profesor(user_id, horario):
    """
    Actualiza el horario de un profesor en la tabla Usuarios
    
    Args:
        user_id: ID del usuario (profesor)
        horario: Horario en formato string
        
    Returns:
        bool: True si se actualizó correctamente, False en caso contrario
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Actualizar directamente en la tabla Usuarios
        cursor.execute(
            "UPDATE Usuarios SET Horario = ? WHERE Id_usuario = ?",
            (horario, user_id)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        import logging
        logger = logging.getLogger('db.queries')
        logger.error(f"Error al actualizar horario de profesor: {e}")
        return False

# ===== FUNCIONES DE MATRÍCULA =====
def crear_matricula(user_id, asignatura_id, tipo_usuario=None, curso="Actual"):
    """
    Crea o actualiza una matrícula para un usuario en una asignatura
    
    Args:
        user_id: ID del usuario
        asignatura_id: ID de la asignatura
        tipo_usuario: Tipo de usuario para esta matrícula (opcional)
        curso: Curso académico (opcional)
        
    Returns:
        int: ID de la matrícula creada, o None si hubo error
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si ya existe la matrícula
        cursor.execute(
            "SELECT * FROM Matriculas WHERE Id_usuario = ? AND Id_asignatura = ?", 
            (user_id, asignatura_id)
        )
        existe = cursor.fetchone()
        
        if not existe:
            # Si no se proporciona tipo, obtenerlo del usuario
            if tipo_usuario is None:
                cursor.execute("SELECT Tipo FROM Usuarios WHERE Id_usuario = ?", (user_id,))
                user = cursor.fetchone()
                if user:
                    tipo_usuario = user[0]
            
            # Crear matrícula con el tipo obtenido
            cursor.execute(
                "INSERT INTO Matriculas (Id_usuario, Id_asignatura, Tipo, Curso) VALUES (?, ?, ?, ?)",
                (user_id, asignatura_id, tipo_usuario, curso)
            )
            matricula_id = cursor.lastrowid
            conn.commit()
        else:
            # Ya existe, actualizar tipo y curso si se proporcionan
            matricula_id = existe['id_matricula']
            updates = {}
            if tipo_usuario is not None:
                updates['Tipo'] = tipo_usuario
            if curso != "Actual":
                updates['Curso'] = curso
                
            if updates:
                set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
                values = list(updates.values())
                values.append(matricula_id)
                
                cursor.execute(f"UPDATE Matriculas SET {set_clause} WHERE id_matricula = ?", values)
                conn.commit()
                
        conn.close()
        return matricula_id
        
    except Exception as e:
        logger.error(f"Error al crear matrícula: {e}")
        return None

def get_matriculas_by_user(user_id):
    """Obtiene las matrículas de un usuario con información de asignaturas"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            m.id_matricula, 
            m.Id_usuario, 
            m.Id_asignatura, 
            m.Curso, 
            a.Nombre as Asignatura,
            u.Carrera as Carrera
        FROM 
            Matriculas m
        JOIN 
            Asignaturas a ON m.Id_asignatura = a.Id_asignatura
        JOIN
            Usuarios u ON m.Id_usuario = u.Id_usuario
        WHERE 
            m.Id_usuario = ?
    """, (user_id,))
    
    matriculas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return matriculas

def verificar_estudiante_matriculado(estudiante_id, asignatura_id):
    """Verifica si un estudiante está matriculado en una asignatura"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM Matriculas
        WHERE Id_usuario = ? AND Id_asignatura = ?
    """, (estudiante_id, asignatura_id))
    
    result = cursor.fetchone()
    conn.close()
    
    return result['count'] > 0

def get_matriculas_usuario(user_id):
    """Obtiene las matrículas de un usuario incluyendo nombres de asignatura"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT m.*, a.Nombre as Asignatura 
            FROM Matriculas m
            JOIN Asignaturas a ON m.Id_asignatura = a.Id_asignatura
            WHERE m.Id_usuario = ?
        """, (user_id,))
        
        # Convertir filas a diccionarios para facilitar su uso
        result = [dict(row) for row in cursor.fetchall()]
        return result
    except Exception as e:
        print(f"Error al obtener matrículas: {e}")
        return []
    finally:
        conn.close()

# ===== FUNCIONES DE GRUPOS =====
def crear_grupo_tutoria(profesor_id, nombre_sala, tipo_sala, asignatura_id, chat_id, enlace=None, proposito=None):
    """Crea un nuevo grupo de tutoría en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO Grupos_tutoria 
            (Id_usuario, Nombre_sala, Tipo_sala, Id_asignatura, Chat_id, Enlace_invitacion, Proposito_sala) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (profesor_id, nombre_sala, tipo_sala, asignatura_id, str(chat_id), enlace, proposito))
        
        conn.commit()
        grupo_id = cursor.lastrowid
        return grupo_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def crear_grupo_tutoria_directo(conn, profesor_id, nombre_sala, tipo_sala, asignatura_id, chat_id, enlace=None):
    """
    Versión adaptada de crear_grupo_tutoria que utiliza una conexión existente
    y es compatible con la estructura actual de la base de datos
    """
    try:
        cursor = conn.cursor()
        
        # Primera inserción - Grupo (usando el nombre correcto de la columna: Enlace_invitacion)
        cursor.execute("""
            INSERT INTO Grupos_tutoria 
            (Id_usuario, Nombre_sala, Tipo_sala, Id_asignatura, Chat_id, Proposito_sala, Enlace_invitacion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (profesor_id, nombre_sala, tipo_sala, asignatura_id, chat_id, 
              'avisos' if tipo_sala == 'pública' else 'individual', enlace))
        
        # Obtener el ID generado del grupo
        grupo_id = cursor.lastrowid
        
        # Añadir al profesor como miembro del grupo (en lugar de usar Administradores_Grupo)
        cursor.execute("""
            INSERT INTO Miembros_Grupo (id_sala, Id_usuario, Estado)
            VALUES (?, ?, 'activo')
        """, (grupo_id, profesor_id))
        
        return grupo_id
    except Exception as e:
        print(f"Error en crear_grupo_tutoria_directo: {e}")
        conn.rollback()
        return None

def actualizar_grupo_tutoria(grupo_id, **kwargs):
    """
    Actualiza la información de un grupo de tutoría
    
    Args:
        grupo_id: ID del grupo a actualizar
        **kwargs: Campos a actualizar (Chat_id, Enlace_invitacion, etc.)
        
    Returns:
        bool: True si se actualizó correctamente
    """
    if not kwargs:
        return False
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Construir consulta dinámica
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values())
        values.append(grupo_id)
        
        cursor.execute(f"UPDATE Grupos_tutoria SET {set_clause} WHERE id_sala = ?", values)
        
        success = cursor.rowcount > 0
        conn.commit()
        return success
    except Exception as e:
        conn.rollback()
        logger.error(f"Error al actualizar grupo de tutoría: {e}")
        return False
    finally:
        conn.close()

def obtener_grupos(profesor_id=None, asignatura_id=None):
    """
    Obtiene grupos de tutoría aplicando filtros opcionales
    
    Args:
        profesor_id: ID del profesor (opcional)
        asignatura_id: ID de la asignatura (opcional)
        
    Returns:
        list: Lista de grupos que cumplen los criterios
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT g.*, a.Nombre as Asignatura, u.Nombre as Profesor, u.Apellidos as Apellidos_Profesor
        FROM Grupos_tutoria g
        LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
        JOIN Usuarios u ON g.Id_usuario = u.Id_usuario
        WHERE 1=1
    """
    params = []
    
    if profesor_id is not None:
        query += " AND g.Id_usuario = ?"
        params.append(profesor_id)
    
    if asignatura_id is not None:
        query += " AND g.Id_asignatura = ?"
        params.append(asignatura_id)
    
    # Añadir condición para mostrar solo grupos válidos
    query += " AND g.Chat_id IS NOT NULL"
    
    cursor.execute(query, params)
    
    grupos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return grupos

def obtener_grupos_por_asignaturas(asignaturas_ids):
    """Obtiene grupos de tutorías para múltiples asignaturas"""
    if not asignaturas_ids:
        return []
        
    placeholders = ",".join(["?" for _ in asignaturas_ids])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT g.*, a.Nombre as Asignatura, u.Nombre as Profesor, u.Apellidos as Apellidos_Profesor
        FROM Grupos_tutoria g
        JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
        JOIN Usuarios u ON g.Id_usuario = u.Id_usuario
        WHERE g.Id_asignatura IN ({placeholders}) AND g.Chat_id IS NOT NULL
        ORDER BY u.Nombre, g.Nombre_sala
    """, asignaturas_ids)
    
    grupos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return grupos

def obtener_grupo_por_id(grupo_id):
    """Obtiene un grupo de tutoría por su ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT g.*, a.Nombre as Asignatura, u.Nombre as Profesor, u.Apellidos as Apellidos_Profesor
        FROM Grupos_tutoria g
        LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
        JOIN Usuarios u ON g.Id_usuario = u.Id_usuario
        WHERE g.id_sala = ?
    """, (grupo_id,))
    
    grupo = cursor.fetchone()
    conn.close()
    
    return dict(grupo) if grupo else None

def añadir_estudiante_grupo(grupo_id, estudiante_id):
    """Añade un estudiante a un grupo de tutoría"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO Miembros_Grupo (id_sala, Id_usuario)
            VALUES (?, ?)
        """, (grupo_id, estudiante_id))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # El estudiante ya está en el grupo
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error al añadir estudiante al grupo: {e}")
        return False
    finally:
        conn.close()

# ===== PROFESORES Y HORARIOS =====
def obtener_profesores_por_asignaturas(asignaturas_ids):
    """Obtiene profesores que imparten las asignaturas especificadas"""
    if not asignaturas_ids:
        return []
        
    placeholders = ",".join(["?" for _ in asignaturas_ids])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT DISTINCT u.Id_usuario, u.Nombre, u.Apellidos, u.Email_UGR, hp.dia || ' de ' || hp.hora_inicio || ' a ' || hp.hora_fin AS Horario
        FROM Usuarios u
        JOIN Matriculas m ON u.Id_usuario = m.Id_usuario
        LEFT JOIN Horarios_Profesores hp ON u.Id_usuario = hp.Id_usuario
        WHERE u.Tipo = 'profesor' AND m.Id_asignatura IN ({placeholders})
    """, asignaturas_ids)
    
    profesores = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return profesores

def get_horarios_profesor(profesor_id):
    """Obtiene el horario de un profesor desde la tabla Usuarios"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT 
                Id_usuario,
                Nombre,
                Horario
            FROM 
                Usuarios
            WHERE 
                Id_usuario = ? AND Tipo = 'profesor'
        ''', (profesor_id,))
        
        result = cursor.fetchone()
        
        if not result or not result['Horario']:
            print(f"No se encontró horario para profesor ID: {profesor_id}")
            return None
            
        return result['Horario']
    except Exception as e:
        import logging
        logging.getLogger('db.queries').error(f"Error al obtener horario: {e}")
        return None
    finally:
        conn.close()

def verificar_disponibilidad_profesor(profesor_id):
    """Verifica si un profesor está disponible actualmente según su horario"""
    from handlers.tutorias import verificar_horario_tutoria
    
    # Obtener horario del profesor
    horario = get_horarios_profesor(profesor_id)
    
    # Si no hay horario registrado, asumir no disponible
    if not horario:
        return False
        
    # Verificar si estamos en horario de tutoría
    return verificar_horario_tutoria(horario)

# ===== ASIGNATURAS Y CARRERAS =====
def get_o_crear_carrera(nombre_carrera):
    """Obtiene una carrera por nombre o la crea si no existe"""
    if not nombre_carrera or nombre_carrera.strip() == '':
        return None  # No crear carreras vacías
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Buscar la carrera por nombre
        cursor.execute("SELECT id_carrera FROM Carreras WHERE Nombre_carrera = ?", (nombre_carrera,))
        carrera = cursor.fetchone()
        
        if carrera:
            # La carrera ya existe
            carrera_id = carrera[0]
        else:
            # Crear nueva carrera
            cursor.execute("INSERT INTO Carreras (Nombre_carrera) VALUES (?)", (nombre_carrera,))
            carrera_id = cursor.lastrowid
            conn.commit()
            
        return carrera_id
        
    except Exception as e:
        print(f"Error al obtener/crear carrera: {e}")
        return None
        
    finally:
        conn.close()

def get_carreras():
    """Obtiene todas las carreras"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id_carrera, Nombre_carrera FROM Carreras ORDER BY Nombre_carrera")
    carreras = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return carreras

def get_carreras_by_area(area_id=None):
    """
    Función de compatibilidad que mantiene la interfaz anterior.
    Ahora simplemente devuelve todas las carreras sin filtrar por área.
    
    Args:
        area_id: Ignorado, mantenido para compatibilidad
        
    Returns:
        list: Lista de todas las carreras
    """
    # Simplemente llamamos a la nueva función sin filtrado por área
    return get_carreras()

def crear_asignatura(nombre, sigla=None, id_carrera=None):
    """Crea una nueva asignatura en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar columnas existentes
        cursor.execute("PRAGMA table_info(Asignaturas)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        # Construir consulta según columnas disponibles
        if 'Sigla' in columnas and 'Id_carrera' in columnas:
            cursor.execute(
                "INSERT INTO Asignaturas (Nombre, Sigla, Id_carrera) VALUES (?, ?, ?)",
                (nombre, sigla, id_carrera)
            )
        elif 'Sigla' in columnas:
            cursor.execute(
                "INSERT INTO Asignaturas (Nombre, Sigla) VALUES (?, ?)",
                (nombre, sigla)
            )
        else:
            # Sin columna Sigla
            cursor.execute(
                "INSERT INTO Asignaturas (Nombre) VALUES (?)",
                (nombre,)
            )
        
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al crear asignatura: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def crear_matricula(id_usuario, id_asignatura, tipo_usuario='estudiante', verificar_duplicados=True):
    """Crea una nueva matrícula para un usuario en una asignatura"""
    if id_usuario is None or id_asignatura is None:
        print("Error: Usuario o asignatura inválidos")
        return False
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar si ya existe esta matrícula
        if verificar_duplicados:
            cursor.execute(
                "SELECT * FROM Matriculas WHERE Id_usuario = ? AND Id_asignatura = ?",
                (id_usuario, id_asignatura)
            )
            if cursor.fetchone():
                # Ya existe, no hacer nada
                print(f"  ⏩ Matrícula ya existente - omitiendo")
                return True
        
        # Crear nueva matrícula
        cursor.execute(
            "INSERT INTO Matriculas (Id_usuario, Id_asignatura, Tipo) VALUES (?, ?, ?)",
            (id_usuario, id_asignatura, tipo_usuario)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al crear matrícula: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_salas_profesor_asignatura(profesor_id, asignatura_id):
    """
    Obtiene las salas de tutoría de un profesor para una asignatura específica
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT g.*, u.Nombre as NombreProfesor 
        FROM Grupos_tutoria g
        JOIN Usuarios u ON g.Id_usuario = u.Id_usuario
        WHERE g.Id_usuario = ? AND (g.Id_asignatura = ? OR g.Id_asignatura IS NULL)
        ORDER BY g.Proposito_sala ASC
    """, (profesor_id, asignatura_id))
    
    salas = cursor.fetchall()
    conn.close()
    
    return salas if salas else []


def get_profesores_asignatura(asignatura_id):
    """
    Obtiene todos los profesores que imparten una asignatura específica
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT u.*
        FROM Usuarios u
        JOIN Matriculas m ON u.Id_usuario = m.Id_usuario
        WHERE m.Id_asignatura = ? 
        AND u.Tipo = 'profesor' 
        AND m.Tipo = 'docente'
    """, (asignatura_id,))
    
    profesores = cursor.fetchall()
    conn.close()
    
    return profesores if profesores else []
