import sqlite3
from pathlib import Path
import sys
import os
import logging
from db.constantes import *
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

##No se usa
def insert_usuario(nombre, tipo, email, telegram_id=None, apellidos=None, dni=None, carrera=None, area=None, registrado=USUARIO_NO_REGISTRADO, do_commit=True):
    """Crea un nuevo usuario en la base de datos con los datos proporcionados"""
    cursor = get_cursor()
    
    try:
        cursor.execute(
            f"""INSERT INTO {USUARIOS} 
            ({USUARIO_NOMBRE}, {USUARIO_TIPO}, {USUARIO_EMAIL}, {USUARIO_ID_TELEGRAM}, {USUARIO_APELLIDOS}, {USUARIO_DNI}, {USUARIO_CARRERA}, {USUARIO_AREA}, {USUARIO_REGISTRADO}) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (nombre, tipo, email, telegram_id, apellidos, dni, carrera, area, registrado)
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
    if not all(k in USUARIO_CAMPOS_VALIDOS for k in kwargs):
        raise ValueError("Campo inválido en la actualización de usuario")

    try:
        query = f"UPDATE {USUARIOS} SET "
        query += ", ".join([f"{USUARIO_FIELDS[k]} = ?" for k in kwargs])
        query += f" WHERE {USUARIO_ID} = ?"
        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()) + [user_id])
        if do_commit:
            commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al actualizar usuario: {e}")
        rollback()
        return False

##No se usa
def delete_usuario(user_id):
    cursor = get_cursor()
    try:
        cursor.execute(f"DELETE FROM {USUARIOS} WHERE {USUARIO_ID} = ?", (user_id,))
        commit()
    except Exception as e:
        print(f"Error al eliminar usuario: {e}")
        rollback()

def get_usuarios(**kwargs):
    try:
        if not all(k in USUARIO_CAMPOS_VALIDOS for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Usuarios")

        query = f"SELECT * FROM {USUARIOS} WHERE 1=1"
        for k in kwargs:
            query += f" AND {USUARIO_FIELDS[k]} = ?"
            
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
            SELECT * FROM {USUARIOS}
            WHERE {USUARIO_ID} IN ({placeholders})
            ORDER BY {USUARIO_NOMBRE}, {USUARIO_APELLIDOS}
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

##No se usa
def insert_asignatura(nombre, codigo = None, id_carrera = None, do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(
            f"INSERT INTO {ASIGNATURAS} ({ASIGNATURA_NOMBRE}, {ASIGNATURA_CODIGO}, {ASIGNATURA_ID_CARRERA}) VALUES (?, ?, ?)",
            (nombre, codigo, id_carrera)
        )
        if do_commit:
            commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al crear asignatura: {e}")
        rollback()
        return None

##No se usa    
def update_asignatura(asignatura_id, do_commit=True,  **kwargs):
    """Actualiza los datos de una asignatura existente"""
    if not all(k in ASIGNATURA_CAMPOS_VALIDOS for k in kwargs):
        raise ValueError("Campo inválido en la actualización de asignatura")

    try:
        query = f"UPDATE {ASIGNATURAS} SET "
        query += ", ".join([f"{ASIGNATURA_FIELDS[k]} = ?" for k in kwargs])
        query += f" WHERE {ASIGNATURA_ID} = ?"

        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()) + [asignatura_id])
        if do_commit:
            commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al actualizar asignatura: {e}")
        rollback()
        return False

##No se usa
def delete_asignatura(asignatura_id):
    cursor = get_cursor()
    try:
        cursor.execute(f"DELETE FROM {ASIGNATURAS} WHERE {ASIGNATURA_ID} = ?", (asignatura_id,))
        commit()
    except Exception as e:
        print(f"Error al eliminar asignatura: {e}")
        rollback()

def get_asignaturas(**kwargs):
    try:
        if not all(k in ASIGNATURA_CAMPOS_VALIDOS for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Asignaturas")

        query = f"SELECT * FROM {ASIGNATURAS} WHERE 1=1"
        for k in kwargs:
            query += f" AND {ASIGNATURA_FIELDS[k]} = ?"
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

def insert_grupo_tutoria(usuario_id, nombre, tipo, asignatura_id = None, chat_id = None, enlace_invitacion = None, proposito = None, do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(
            f"""INSERT INTO {GRUPOS} 
            ({GRUPO_ID_USUARIO}, {GRUPO_NOMBRE}, {GRUPO_TIPO}, {GRUPO_ID_ASIGNATURA}, {GRUPO_ID_CHAT}, {GRUPO_ENLACE}, {GRUPO_PROPOSITO}) 
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (usuario_id, nombre, tipo, asignatura_id, chat_id, enlace_invitacion, proposito)
        )
        
        if do_commit:
            commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al crear grupo de tutoría: {e}")
        rollback()
        return None

##No se usa    
def update_grupo_tutoria(grupo_id, do_commit=True, **kwargs):
    """Actualiza los datos de una grupo de tutoría"""
    if not all(k in GRUPO_CAMPOS_VALIDOS for k in kwargs):
        raise ValueError("Campo inválido en la actualización del grupo de tutoría")

    try:
        query = f"UPDATE {GRUPOS} SET "
        query += ", ".join([f"{GRUPO_FIELDS[k]} = ?" for k in kwargs])
        query += f" WHERE {GRUPO_ID} = ?"

        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()) + [grupo_id])
        if do_commit:
            commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al actualizar grupo_tutoria: {e}")
        rollback()
        return False

def delete_grupo_tutoria(grupo_id):
    cursor = get_cursor()
    try:
        cursor.execute(f"DELETE FROM {GRUPOS} WHERE {GRUPO_ID} = ?", (grupo_id,))
        commit()
    except Exception as e:
        print(f"Error al eliminar grupo de tutoría: {e}")
        rollback()

def get_grupos_tutoria(**kwargs):
    try:
        if not all(k in GRUPO_CAMPOS_VALIDOS for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Grupos_tutoria")

        query = f"""SELECT g.*, a.{ASIGNATURA_NOMBRE} as Asignatura, u.{USUARIO_NOMBRE} as Profesor, u.{USUARIO_APELLIDOS} as Apellidos_Profesor
            FROM {GRUPOS} g
            LEFT JOIN {ASIGNATURAS} a ON g.{GRUPO_ID_ASIGNATURA} = a.{ASIGNATURA_ID}
            JOIN {USUARIOS} u ON g.{GRUPO_ID_USUARIO} = u.{USUARIO_ID}
            WHERE 1=1"""
        for k in kwargs:
            query += f" AND g.{GRUPO_FIELDS[k]} = ?"

        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al obtener grupo de tutoría: {e}")
        rollback()
        return None

    

##=======================
## ===== Matriculas =====
##=======================

##No se usa
def insert_matricula(usuario_id, asignatura_id, curso, tipo, do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(
            f"INSERT INTO {MATRICULAS} ({MATRICULA_ID_USUARIO}, {MATRICULA_ID_ASIGNATURA}, {MATRICULA_CURSO}, {MATRICULA_TIPO}) VALUES (?, ?, ?, ?)",
            (usuario_id, asignatura_id, curso, tipo)
        )
        if do_commit:
            commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al crear matrícula: {e}")
        rollback()
        return None

##No se usa    
def update_matricula(matricula_id, do_commit=True, **kwargs):
    """Actualiza los datos de una matrícula"""
    if not all(k in MATRICULA_CAMPOS_VALIDOS for k in kwargs):
        raise ValueError("Campo inválido en la actualización de matrícula")

    try:
        query = f"UPDATE {MATRICULAS} SET "
        query += ", ".join([f"{MATRICULA_FIELDS[k]} = ?" for k in kwargs])
        query += f" WHERE {MATRICULA_ID} = ?"

        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()) + [matricula_id])
        if do_commit:
            commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al actualizar matrícula: {e}")
        rollback()
        return False

##No se usa
def delete_matricula(matricula_id):
    cursor = get_cursor()
    try:
        cursor.execute(f"DELETE FROM {MATRICULAS} WHERE {MATRICULA_ID} = ?", (matricula_id,))
        commit()
    except Exception as e:
        print(f"Error al eliminar matrícula: {e}")
        rollback()

def get_matriculas(**kwargs):
    try:
        if not all(k in MATRICULA_CAMPOS_VALIDOS for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Matriculas")

        query = f"""SELECT m.*, a.{ASIGNATURA_NOMBRE} AS Asignatura, a.{ASIGNATURA_CODIGO} AS Codigo, u.{USUARIO_CARRERA} AS Carrera 
                    FROM {MATRICULAS} m
                    JOIN 
                    {ASIGNATURAS} a ON m.{MATRICULA_ID_ASIGNATURA} = a.{ASIGNATURA_ID}
                    JOIN
                    {USUARIOS} u ON m.{MATRICULA_ID_USUARIO} = u.{USUARIO_ID}
                    WHERE 1=1"""
        for k in kwargs:
            query += f" AND m.{MATRICULA_FIELDS[k]} = ?"
        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al obtener matrícula(s): {e}")
        rollback()
        return None



##=========================
## ===== Valoraciones =====
##=========================



def insert_valoracion(evaluador_id, profesor_id, puntuacion, comentario, fecha, es_anonimo, grupo_id, do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(
            f"""INSERT INTO {VALORACIONES} ({VALORACION_ID_EVALUADOR}, {VALORACION_ID_PROFESOR}, {VALORACION_PUNTUACION}, {VALORACION_COMENTARIO}, {VALORACION_FECHA}, {VALORACION_ES_ANONIMA}, {VALORACION_ID_SALA})
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (evaluador_id, profesor_id, puntuacion, comentario, fecha, es_anonimo, grupo_id)
        )
        if do_commit:
            commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al crear valoración: {e}")
        rollback()
        return None
    
##No se usa
def update_valoracion(valoracion_id, do_commit=True, **kwargs):
    """Actualiza los datos de una valoración"""
    if not all(k in VALORACION_CAMPOS_VALIDOS for k in kwargs):
        raise ValueError("Campo inválido en la actualización de valoración")

    try:
        query = f"UPDATE {VALORACIONES} SET "
        query += ", ".join([f"{VALORACION_FIELDS[k]} = ?" for k in kwargs])
        query += f" WHERE {VALORACION_ID} = ?"

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
        cursor.execute(f"DELETE FROM {VALORACIONES} WHERE {VALORACION_ID} = ?", (id_valoracion,))
        commit()
    except Exception as e:
        print(f"Error al eliminar valoración: {e}")
        rollback()

def get_valoraciones(**kwargs):
    try:
        if not all(k in VALORACION_CAMPOS_VALIDOS for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Valoraciones")

        query = f"SELECT * FROM {VALORACIONES} WHERE 1=1"
        for k in kwargs:
            query += f" AND {VALORACION_FIELDS[k]} = ?"
            
        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al obtener valoración(es): {e}")
        rollback()
        return None
