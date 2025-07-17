from pathlib import Path
import sys
import os
import logging
from db import get_cursor, commit, rollback
from db.constantes import *

# Configurar logger
logger = logging.getLogger(__name__)

##=====================
## ===== Usuarios =====
##=====================

##No se usa
def insert_usuario(nombre, tipo, email, telegram_id=None, apellidos=None, do_commit=True):
    """Crea un nuevo usuario en la base de datos con los datos proporcionados"""
    cursor = get_cursor()
    
    try:
        cursor.execute(
            f"""INSERT INTO {USUARIOS} 
            ({USUARIO_NOMBRE}, {USUARIO_TIPO}, {USUARIO_EMAIL}, {USUARIO_ID_TELEGRAM}, {USUARIO_APELLIDOS}) 
            VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})""",
            (nombre, tipo, email, telegram_id, apellidos)
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
        query += ", ".join([f"{USUARIO_FIELDS[k]} = {PLACEHOLDER}" for k in kwargs])
        query += f" WHERE {USUARIO_ID} = {PLACEHOLDER}"
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
        cursor.execute(f"DELETE FROM {USUARIOS} WHERE {USUARIO_ID} = {PLACEHOLDER}", (user_id,))
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
            query += f" AND {USUARIO_FIELDS[k]} = {PLACEHOLDER}"
            
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
        placeholders = ",".join([f"{PLACEHOLDER}" for _ in usuarios_ids])
        query = f"""
            SELECT * FROM {USUARIOS}
            WHERE {USUARIO_ID} IN ({placeholders})
            ORDER BY {USUARIO_NOMBRE}, {USUARIO_APELLIDOS}
        """

        print(query)

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
def insert_asignatura(nombre, do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(
            f"INSERT INTO {ASIGNATURAS} ({ASIGNATURA_NOMBRE}) VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})",
            (nombre)
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
        query += ", ".join([f"{ASIGNATURA_FIELDS[k]} = {PLACEHOLDER}" for k in kwargs])
        query += f" WHERE {ASIGNATURA_ID} = {PLACEHOLDER}"

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
        cursor.execute(f"DELETE FROM {ASIGNATURAS} WHERE {ASIGNATURA_ID} = {PLACEHOLDER}", (asignatura_id,))
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
            query += f" AND {ASIGNATURA_FIELDS[k]} = {PLACEHOLDER}"
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

def insert_grupo_tutoria(usuario_id, nombre, tipo, asignatura_id = None, chat_id = None, enlace_invitacion = None, do_commit=True):
    cursor = get_cursor()
    try:
        query = f"""INSERT INTO {GRUPOS} ({GRUPO_ID_PROFESOR}, {GRUPO_NOMBRE}, {GRUPO_TIPO}, {GRUPO_ID_ASIGNATURA}, {GRUPO_ID_CHAT}, {GRUPO_ENLACE}) 
            VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})"""
        
        cursor.execute(query, (usuario_id, nombre, tipo, asignatura_id, chat_id, enlace_invitacion))        
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
        query += ", ".join([f"{GRUPO_FIELDS[k]} = {PLACEHOLDER}" for k in kwargs])
        query += f" WHERE {GRUPO_ID} = {PLACEHOLDER}"
        
        print(query)
        
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
        cursor.execute(f"DELETE FROM {GRUPOS} WHERE {GRUPO_ID} = {PLACEHOLDER}", (grupo_id,))
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
            JOIN {USUARIOS} u ON g.{GRUPO_ID_PROFESOR} = u.{USUARIO_ID}
            WHERE 1=1"""
        
        for k in kwargs:
            query += f" AND g.{GRUPO_FIELDS[k]} = {PLACEHOLDER}"

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
def insert_matricula(usuario_id, asignatura_id, tipo, do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(
            f"INSERT INTO {MATRICULAS} ({MATRICULA_ID_USUARIO}, {MATRICULA_ID_ASIGNATURA}, {MATRICULA_TIPO}) VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})",
            (usuario_id, asignatura_id, tipo)
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
        query += ", ".join([f"{MATRICULA_FIELDS[k]} = {PLACEHOLDER}" for k in kwargs])
        query += f" WHERE {MATRICULA_ID} = {PLACEHOLDER}"

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
        cursor.execute(f"DELETE FROM {MATRICULAS} WHERE {MATRICULA_ID} = {PLACEHOLDER}", (matricula_id,))
        commit()
    except Exception as e:
        print(f"Error al eliminar matrícula: {e}")
        rollback()

def get_matriculas(**kwargs):
    try:
        if not all(k in MATRICULA_CAMPOS_VALIDOS for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Matriculas")

        query = f"""SELECT m.*, a.{ASIGNATURA_NOMBRE} AS Asignatura
                    FROM {MATRICULAS} m
                    JOIN 
                    {ASIGNATURAS} a ON m.{MATRICULA_ID_ASIGNATURA} = a.{ASIGNATURA_ID}
                    JOIN
                    {USUARIOS} u ON m.{MATRICULA_ID_USUARIO} = u.{USUARIO_ID}
                    WHERE 1=1"""
        for k in kwargs:
            query += f" AND m.{MATRICULA_FIELDS[k]} = {PLACEHOLDER}"
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



def insert_valoracion(evaluador_id, profesor_id, puntuacion, comentario, fecha, es_anonimo, do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(
            f"""INSERT INTO {VALORACIONES} ({VALORACION_ID_EVALUADOR}, {VALORACION_ID_PROFESOR}, {VALORACION_PUNTUACION}, {VALORACION_COMENTARIO}, {VALORACION_FECHA}, {VALORACION_ANONIMA})
            VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})""",
            (evaluador_id, profesor_id, puntuacion, comentario, fecha, es_anonimo)
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
        query += ", ".join([f"{VALORACION_FIELDS[k]} = {PLACEHOLDER}" for k in kwargs])
        query += f" WHERE {VALORACION_ID} = {PLACEHOLDER}"

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
        cursor.execute(f"DELETE FROM {VALORACIONES} WHERE {VALORACION_ID} = {PLACEHOLDER}", (id_valoracion,))
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
            query += f" AND {VALORACION_FIELDS[k]} = {PLACEHOLDER}"
            
        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al obtener valoración(es): {e}")
        rollback()
        return None
