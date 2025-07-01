import sqlite3
from pathlib import Path
import sys
import os
import logging
from db.db import get_cursor, commit, rollback

# Configurar logger
logger = logging.getLogger(__name__)

# Añadir directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ruta a la base de datos
DB_PATH = Path(__file__).parent.parent / "tutoria_ugr.db"

##=====================
## ===== Usuarios =====
##=====================

def insert_usuario(nombre, tipo, email, telegram_id=None, apellidos=None, dni=None, carrera=None, Area=None, registrado="NO", do_commit=True):
    """Crea un nuevo usuario en la base de datos con los datos proporcionados"""
    cursor = get_cursor()
    
    try:
        cursor.execute(
            """INSERT INTO Usuarios 
            (Nombre, Tipo, Email_UGR, TelegramID, Apellidos, DNI, Carrera, Area, Registrado) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (nombre, tipo, email, telegram_id, apellidos, dni, carrera, Area, registrado)
        )
        if do_commit:
            commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al crear usuario: {e}")
        rollback()
        return None
    
def update_usuario(user_id, do_commit = True, **kwargs):
    """Actualiza los datos de un usuario existente"""
    allowed_fields = {"Nombre", "Apellidos", "DNI", "Tipo", "Email_UGR", "TelegramID", "Registrado", "Area", "Carrera", "Horario"}
    if not all(k in allowed_fields for k in kwargs):
        raise ValueError("Campo inválido en la actualización de usuario")

    try:
        query = "UPDATE Usuarios SET "
        query += ", ".join([f"{k} = ?" for k in kwargs])
        query += " WHERE Id_usuario = ?"
        print(query)
        print(list(kwargs.values()) + [user_id])
        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()) + [user_id])
        print(query)
        if do_commit:
            commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al actualizar usuario: {e}")
        rollback()
        return False

def delete_usuario(user_id):
    cursor = get_cursor()
    try:
        cursor.execute("DELETE FROM Usuarios WHERE Id_usuario = ?", (user_id,))
        commit()
    except Exception as e:
        print(f"Error al eliminar usuario: {e}")
        rollback()

def get_usuarios(**kwargs):
    allowed_fields = {
        "Id_usuario", "Nombre", "Apellidos", "DNI", "Tipo", "Email_UGR",
        "TelegramID", "Registrado", "Area", "Carrera", "Horario"
    }
    try:
        if not all(k in allowed_fields for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Usuarios")

        query = "SELECT * FROM Usuarios WHERE 1=1"
        for k in kwargs:
            query += f" AND {k} = ?"
        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al obtener usuario(s): {e}")
        rollback()
        return None
    
def get_usuarios_by_multiple_ids(usuarios_ids):
    """Obtiene usuarios a partir de una lista de IDs"""
    if not usuarios_ids:
        return []

    cursor = get_cursor()

    try:
        placeholders = ",".join(["?" for _ in usuarios_ids])
        query = f"""
            SELECT * FROM Usuarios
            WHERE Id_usuario IN ({placeholders})
            ORDER BY Nombre, Apellidos
        """
        cursor.execute(query, usuarios_ids)
        return [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        import logging
        logging.getLogger("db.queries").error(f"Error al obtener usuarios por IDs: {e}")
        return []



##========================
## ===== Asignaturas =====
##========================

def insert_asignatura(nombre, codigo, id_carrera = None, do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(
            "INSERT INTO Asignaturas (Nombre, Codigo_Asignatura, Id_carrera) VALUES (?, ?, ?)",
            (nombre, codigo, id_carrera)
        )
        if do_commit:
            commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al crear asignatura: {e}")
        rollback()
        return None
    
def update_asignatura(asignatura_id, do_commit=True,  **kwargs):
    """Actualiza los datos de una asignatura existente"""
    allowed_fields = {"Nombre", "Codigo_Asignatura", "Id_carrera"}
    if not all(k in allowed_fields for k in kwargs):
        raise ValueError("Campo inválido en la actualización de asignatura")

    try:
        query = "UPDATE Asignaturas SET "
        query += ", ".join([f"{k} = ?" for k in kwargs])
        query += " WHERE Id_asignatura = ?"

        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()) + [asignatura_id])
        if do_commit:
            commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al actualizar asignatura: {e}")
        rollback()
        return False

def delete_asignatura(asignatura_id):
    cursor = get_cursor()
    try:
        cursor.execute("DELETE FROM Asignaturas WHERE Id_asignatura = ?", (asignatura_id,))
        commit()
    except Exception as e:
        print(f"Error al eliminar asignatura: {e}")
        rollback()

def get_asignaturas(**kwargs):
    allowed_fields = {"Id_asignatura", "Nombre", "Codigo_Asignatura", "Id_carrera"}
    try:
        if not all(k in allowed_fields for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Asignaturas")

        query = "SELECT * FROM Asignaturas WHERE 1=1"
        for k in kwargs:
            query += f" AND {k} = ?"
        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al obtener asignatura(s): {e}")
        rollback()
        return None



##===========================
## ===== Grupos_tutoria =====
##===========================

def insert_grupo_tutoria(id_usuario, nombre_sala, tipo_sala, id_asignatura = None, chat_id = None, enlace_invitacion = None, proposito_sala = None, do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(
            """INSERT INTO Grupos_tutoria 
            (Id_usuario, Nombre_sala, Tipo_sala, Id_asignatura, Chat_id, Enlace_invitacion, Proposito_sala) 
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (id_usuario, nombre_sala, tipo_sala, id_asignatura, chat_id, enlace_invitacion, proposito_sala)
        )
        if do_commit:
            commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al crear grupo de tutoría: {e}")
        rollback()
        return None
    
def update_grupo_tutoria(sala_id, do_commit=True, **kwargs):
    """Actualiza los datos de una sala de tutoría"""
    allowed_fields = {"Id_usuario", "Nombre_sala", "Tipo_sala", "Id_asignatura", "Chat_id", "Enlace_invitacion", "Proposito_sala"}
    if not all(k in allowed_fields for k in kwargs):
        raise ValueError("Campo inválido en la actualización del grupo de tutoría")

    try:
        query = "UPDATE Grupos_tutoria SET "
        query += ", ".join([f"{k} = ?" for k in kwargs])
        query += " WHERE id_sala = ?"

        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()) + [sala_id])
        if do_commit:
            commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al actualizar grupo_tutoria: {e}")
        rollback()
        return False

def delete_grupo_tutoria(id_sala):
    cursor = get_cursor()
    try:
        cursor.execute("DELETE FROM Grupos_tutoria WHERE id_sala = ?", (id_sala,))
        commit()
    except Exception as e:
        print(f"Error al eliminar grupo de tutoría: {e}")
        rollback()

def get_grupos_tutoria(**kwargs):
    allowed_fields = {
        "id_sala", "Id_usuario", "Nombre_sala", "Tipo_sala", "Id_asignatura",
        "Chat_id", "Enlace_invitacion", "Proposito_sala", "Fecha_creacion"
    }
    try:
        if not all(k in allowed_fields for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Grupos_tutoria")

        query = """SELECT g.*, a.Nombre as Asignatura, u.Nombre as Profesor, u.Apellidos as Apellidos_Profesor
            FROM Grupos_tutoria g
            LEFT JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
            JOIN Usuarios u ON g.Id_usuario = u.Id_usuario
            WHERE 1=1"""
        for k in kwargs:
            query += f" AND g.{k} = ?"

        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al obtener grupo de tutoría: {e}")
        rollback()
        return None

def get_grupos_tutoria_by_multiple_ids(asignaturas_ids):
    """Obtiene grupos de tutorías para múltiples asignaturas"""
    if not asignaturas_ids:
        return []

    cursor = get_cursor()

    try:
        placeholders = ",".join(["?" for _ in asignaturas_ids])

        cursor.execute(f"""
            SELECT g.*, a.Nombre as Asignatura, u.Nombre as Profesor, u.Apellidos as Apellidos_Profesor
            FROM Grupos_tutoria g
            JOIN Asignaturas a ON g.Id_asignatura = a.Id_asignatura
            JOIN Usuarios u ON g.Id_usuario = u.Id_usuario
            WHERE g.Id_asignatura IN ({placeholders}) AND g.Chat_id IS NOT NULL
            ORDER BY u.Nombre, g.Nombre_sala
        """, asignaturas_ids)

        return [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        import logging
        logging.getLogger("db.queries").error(f"Error al obtener grupos por asignaturas: {e}")
        return []
    


##=====================
## ===== Horarios =====
##=====================

def insert_horario(id_usuario, dia, hora_inicio, hora_fin, do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(
            "INSERT INTO Horarios_Profesores (Id_usuario, dia, hora_inicio, hora_fin) VALUES (?, ?, ?, ?)",
            (id_usuario, dia, hora_inicio, hora_fin)
        )
        if do_commit:
            commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al crear horario de profesor: {e}")
        rollback()
        return None
    
def update_horario(horario_id, do_commit=True, **kwargs):
    """Actualiza los datos de un horario de profesor"""
    allowed_fields = {"Id_usuario", "dia", "hora_inicio", "hora_fin"}
    if not all(k in allowed_fields for k in kwargs):
        raise ValueError("Campo inválido en la actualización del horario")

    try:
        query = "UPDATE Horarios_Profesores SET "
        query += ", ".join([f"{k} = ?" for k in kwargs])
        query += " WHERE id_horario = ?"

        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()) + [horario_id])
        if do_commit:
            commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al actualizar horario: {e}")
        rollback()
        return False

def delete_horario(id_horario):
    cursor = get_cursor()
    try:
        cursor.execute("DELETE FROM Horarios_Profesores WHERE id_horario = ?", (id_horario,))
        commit()
    except Exception as e:
        print(f"Error al eliminar horario de profesor: {e}")
        rollback()

def get_horarios(**kwargs):
    allowed_fields = {"id_horario", "Id_usuario", "dia", "hora_inicio", "hora_fin"}
    try:
        if not all(k in allowed_fields for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Horarios_Profesores")

        query = "SELECT * FROM Horarios_Profesores WHERE 1=1"
        for k in kwargs:
            query += f" AND {k} = ?"
        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al obtener horario de profesor: {e}")
        rollback()
        return None


##=======================
## ===== Matriculas =====
##=======================

def insert_matricula(id_usuario, id_asignatura, curso, tipo, do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(
            "INSERT INTO Matriculas (Id_usuario, Id_asignatura, Curso, Tipo) VALUES (?, ?, ?, ?)",
            (id_usuario, id_asignatura, curso, tipo)
        )
        if do_commit:
            commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al crear matrícula: {e}")
        rollback()
        return None
    
def update_matricula(matricula_id, do_commit=True, **kwargs):
    """Actualiza los datos de una matrícula"""
    allowed_fields = {"Id_usuario", "Id_asignatura", "Curso", "Tipo"}
    if not all(k in allowed_fields for k in kwargs):
        raise ValueError("Campo inválido en la actualización de matrícula")

    try:
        query = "UPDATE Matriculas SET "
        query += ", ".join([f"{k} = ?" for k in kwargs])
        query += " WHERE id_matricula = ?"

        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()) + [matricula_id])
        if do_commit:
            commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al actualizar matrícula: {e}")
        rollback()
        return False

def delete_matricula(id_matricula):
    cursor = get_cursor()
    try:
        cursor.execute("DELETE FROM Matriculas WHERE id_matricula = ?", (id_matricula,))
        commit()
    except Exception as e:
        print(f"Error al eliminar matrícula: {e}")
        rollback()

def get_matriculas(**kwargs):
    allowed_fields = {"id_matricula", "Id_usuario", "Id_asignatura", "Curso", "Tipo"}
    try:
        if not all(k in allowed_fields for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Matriculas")

        query = """SELECT m.*, a.Nombre AS Asignatura, a.Codigo_Asignatura AS Codigo, u.Carrera AS Carrera 
                    FROM Matriculas m
                    JOIN 
                    Asignaturas a ON m.Id_asignatura = a.Id_asignatura
                    JOIN
                    Usuarios u ON m.Id_usuario = u.Id_usuario
                    WHERE 1=1"""
        for k in kwargs:
            query += f" AND m.{k} = ?"
        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al obtener matrícula(s): {e}")
        rollback()
        return None



##===========================
## ===== Miembros_Grupo =====
##===========================

def insert_miembro_grupo(id_sala, id_usuario, estado='activo', do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(
            "INSERT INTO Miembros_Grupo (id_sala, Id_usuario, Estado) VALUES (?, ?, ?)",
            (id_sala, id_usuario, estado)
        )
        if do_commit:
            commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al añadir miembro al grupo: {e}")
        rollback()
        return None
    
def update_miembro_grupo(sala_id, usuario_id, estado, do_commit=True):
    """Actualiza los datos de un miembro de grupo"""
    try:
        cursor = get_cursor()
        cursor.execute("UPDATE Miembros_Grupo SET Estado = ? WHERE id_sala = ? AND Id_usuario = ?"
                       , (estado, sala_id, usuario_id))
        if do_commit:
            commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al actualizar miembro_grupo: {e}")
        rollback()
        return False

def delete_miembro_grupo(id_usuario, id_sala):
    cursor = get_cursor()
    try:
        cursor.execute("""
            DELETE FROM Miembros_Grupo 
            WHERE id_usuario = ? AND id_sala = ?
        """, (id_usuario, id_sala))
        commit()
    except Exception as e:
        print(f"Error al eliminar miembro del grupo: {e}")
        rollback()

def delete_todos_miembros_grupo(id_sala):
    cursor = get_cursor()
    try:
        cursor.execute("""
            DELETE FROM Miembros_Grupo 
            WHERE id_sala = ?
        """, (id_sala))
        commit()
    except Exception as e:
        print(f"Error al eliminar miembro del grupo: {e}")
        rollback()

def get_miembros_grupos(**kwargs):
    allowed_fields = {"id_miembro", "id_sala", "Id_usuario", "Fecha_union", "Estado"}
    try:
        if not all(k in allowed_fields for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Miembros_Grupo")

        query = "SELECT * FROM Miembros_Grupo WHERE 1=1"
        for k in kwargs:
            query += f" AND {k} = ?"
        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al obtener miembro(s) del grupo: {e}")
        rollback()
        return None


##=========================
## ===== Valoraciones =====
##=========================

def insert_valoracion(evaluador_id, profesor_id, puntuacion, comentario, fecha, es_anonimo, id_sala, do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(
            """INSERT INTO Valoraciones 
            (evaluador_id, profesor_id, puntuacion, comentario, fecha, es_anonimo, id_sala)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (evaluador_id, profesor_id, puntuacion, comentario, fecha, es_anonimo, id_sala)
        )
        if do_commit:
            commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al crear valoración: {e}")
        rollback()
        return None
    

def update_valoracion(valoracion_id, do_commit=True, **kwargs):
    """Actualiza los datos de una valoración"""
    allowed_fields = {"evaluador_id", "profesor_id", "puntuacion", "comentario", "fecha", "es_anonimo", "id_sala"}
    if not all(k in allowed_fields for k in kwargs):
        raise ValueError("Campo inválido en la actualización de valoración")

    try:
        query = "UPDATE Valoraciones SET "
        query += ", ".join([f"{k} = ?" for k in kwargs])
        query += " WHERE id_valoracion = ?"

        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()) + [valoracion_id])
        if do_commit:
            commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al actualizar valoración: {e}")
        rollback()
        return False

def delete_valoracion(id_valoracion):
    cursor = get_cursor()
    try:
        cursor.execute("DELETE FROM Valoraciones WHERE id_valoracion = ?", (id_valoracion,))
        commit()
    except Exception as e:
        print(f"Error al eliminar valoración: {e}")
        rollback()

def get_valoraciones(**kwargs):
    allowed_fields = {
        "id_valoracion", "evaluador_id", "profesor_id", "puntuacion", "comentario",
        "fecha", "es_anonimo", "id_sala"
    }
    try:
        if not all(k in allowed_fields for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Valoraciones")

        query = "SELECT * FROM Valoraciones WHERE 1=1"
        for k in kwargs:
            query += f" AND {k} = ?"
        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al obtener valoración(es): {e}")
        rollback()
        return None
