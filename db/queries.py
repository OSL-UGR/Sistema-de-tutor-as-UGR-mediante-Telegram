import requests
import logging
from config import MOODLE_URL, MOODLE_TOKEN
from db import get_cursor, commit, rollback
from db.constantes import *

# Configurar logger
logger = logging.getLogger(__name__)

##=====================
## ===== Usuarios =====
##=====================

def create_usuario(moodle_id, telegram_id, tipo, do_commit=True):
    """Crea un nuevo usuario en la base de datos con los datos proporcionados"""
    cursor = get_cursor()
    
    try:
        cursor.execute(
            f"""INSERT INTO {USUARIOS} 
            ({USUARIO_ID_MOODLE}, {USUARIO_ID_TELEGRAM}, {USUARIO_TIPO}) 
            VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})""",
            (moodle_id, telegram_id, tipo)
        )
        if do_commit:
            commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al crear usuario: {e}")
        rollback()
        return None
    
def update_usuario(user_id, do_commit=True, **kwargs):
    """Actualiza únicamente los campos locales Email_UGR y TelegramID de un usuario, identificándolo por Usuario_id."""
    CAMPOS_EDITABLES = {"USUARIO_ID_TELEGRAM", "USUARIO_HORARIO" }

    # Validación estricta: solo campos permitidos
    if not all(k in CAMPOS_EDITABLES for k in kwargs):
        raise ValueError("Solo se pueden actualizar Horario y TelegramID")

    try:
        if not kwargs:
            return False  # Nada que actualizar

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

        cursor = get_cursor()

        # Caso 1: Se filtra por TelegramID
        if "USUARIO_ID" in kwargs or "USUARIO_ID_TELEGRAM" in kwargs:
            field = "USUARIO_ID" if "USUARIO_ID" in kwargs else "USUARIO_ID_TELEGRAM"
            query = f"SELECT * FROM {USUARIOS} WHERE {USUARIO_FIELDS[field]} = {PLACEHOLDER}"
            cursor.execute(query, (kwargs[field],))
            row = cursor.fetchone()
            if row is None:
                return []
            
            usuario_id = row[USUARIO_ID]
            moodle_id = row[USUARIO_ID_MOODLE]
            telegram_id = row[USUARIO_ID_TELEGRAM]
            tipo = row[USUARIO_TIPO]
            horario = row[USUARIO_HORARIO] if USUARIO_HORARIO in row else None

            # Llamada a Moodle por email
            payload = {
                'wstoken': MOODLE_TOKEN,
                'wsfunction': 'core_user_get_users',
                'moodlewsrestformat': 'json',
                'criteria[0][key]': 'id',
                'criteria[0][value]': moodle_id,
            }
            url = f"{MOODLE_URL}/webservice/rest/server.php"
            response = requests.post(url, params=payload)

            if response.ok:
                users = response.json().get("users", [])
                result = []
                for user in users:
                    result.append({
                        USUARIO_ID: usuario_id,
                        USUARIO_ID_MOODLE: moodle_id,
                        USUARIO_ID_TELEGRAM: telegram_id,
                        USUARIO_NOMBRE: user.get("firstname"),
                        USUARIO_APELLIDOS: user.get("lastname"),
                        USUARIO_EMAIL: user.get("email"),
                        USUARIO_TIPO: tipo,
                        USUARIO_HORARIO: horario,
                    })
                return result
            else:
                logging.getLogger('moodle').error(f"Error al consultar Moodle: {response.status_code} - {response.text}")
                return None

        # Caso 2: Otros filtros (nombre, apellidos, etc.) → consultar Moodle y luego completar con datos locales
        else:
            # Construcción de criterios Moodle
            criteria = []
            for i, (k, v) in enumerate(kwargs.items()):
                moodle_key = USUARIO_FIELDS[k].lower()
                if moodle_key not in [USUARIO_ID_MOODLE, USUARIO_EMAIL, USUARIO_NOMBRE, USUARIO_APELLIDOS]:
                    raise ValueError(f"Campo inválido para Moodle: {k}")
                if moodle_key == USUARIO_ID_MOODLE: moodle_key = "id"
                criteria.append((f"criteria[{i}][key]", moodle_key))
                criteria.append((f"criteria[{i}][value]", v))

            payload = {
                'wstoken': MOODLE_TOKEN,
                'wsfunction': 'core_user_get_users',
                'moodlewsrestformat': 'json',
            }
            payload.update(dict(criteria))

            url = f"{MOODLE_URL}/webservice/rest/server.php"
            response = requests.post(url, params=payload)

            if response.ok:
                users = response.json().get("users", [])
                result = []
                for user in users:
                    id_moodle = user.get("id")
                    # Buscar usuario en BD por id
                    query = f"SELECT * FROM {USUARIOS} WHERE {USUARIO_ID_MOODLE} = {PLACEHOLDER}"
                    args = (id_moodle,)
                    if USUARIO_TIPO in kwargs:
                        query += f" AND {USUARIO_TIPO} = {PLACEHOLDER}"
                        args+=(kwargs[USUARIO_TIPO],)
                    cursor.execute(query, args)
                    local = cursor.fetchone()
                    id = local[USUARIO_ID] if local else None
                    telegram_id = local[USUARIO_ID_TELEGRAM] if local else None
                    tipo = local[USUARIO_TIPO] if local else None
                    horario = local[USUARIO_HORARIO] if local and USUARIO_HORARIO in local else None

                    result.append({
                        USUARIO_ID: id,
                        USUARIO_ID_MOODLE: id_moodle,
                        USUARIO_ID_TELEGRAM: telegram_id,
                        USUARIO_NOMBRE: user.get("firstname"),
                        USUARIO_APELLIDOS: user.get("lastname"),
                        USUARIO_EMAIL: user.get("email"),
                        USUARIO_TIPO: tipo,
                        USUARIO_HORARIO: horario,
                    })
                return result
            else:
                logging.getLogger('moodle').error(f"Error al consultar Moodle: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al obtener usuario(s): {e}")
        rollback()
        return None

def get_usuarios_by_multiple_ids_local(usuarios_ids):
    """Obtiene usuarios desde Moodle, complementando con datos locales a partir de una lista de IDs"""
    if not usuarios_ids:
        return []

    cursor = get_cursor()

    try:
        placeholders = ",".join([PLACEHOLDER for _ in usuarios_ids])
        query = f"SELECT * FROM {USUARIOS} WHERE {USUARIO_ID} IN ({placeholders})"
        cursor.execute(query, list(usuarios_ids))
        
        return [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        logging.getLogger("db.queries").error(f"Error al obtener usuarios por IDs: {e}")
        return []

def get_usuarios_local(**kwargs):
    try:
        if not all(k in {"USUARIO_ID", "USUARIO_ID_MOODLE", "USUARIO_ID_TELEGRAM", "USUARIO_TIPO"} for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Usuarios")
        
        query = f"SELECT * FROM {USUARIOS} WHERE 1=1"
        for k in kwargs:
            query += f" AND {USUARIO_FIELDS[k]} = {PLACEHOLDER}"
        
        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al obtener usuarios: {e}")
        rollback()
        return None


##========================
## ===== Asignaturas =====
##========================

def get_asignaturas(**kwargs):
    """
    Busca asignaturas (cursos) en Moodle según su ID, nombre o nombre corto.
    Campos válidos:
        - id: ID del curso en Moodle
        - nombre: nombre completo (fullname)
        - nombrecorto: nombre corto (shortname)
    """
    try:
        if not kwargs:
            raise ValueError("Debe especificar al menos un criterio de búsqueda")
        if not all(k in ASIGNATURA_CAMPOS_VALIDOS for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Asignaturas (permitidos: ASIGNATURA_ID, ASIGNATURA_NOMBRE, ASIGNATURA_NOMBRE_CORTO)")
        if len(kwargs) != 1:
            raise ValueError("Solo se permite un campo de búsqueda a la vez")

        campo = next(iter(kwargs))
        valor = kwargs[campo]

        moodle_field = ASIGNATURA_FIELDS[campo]

        # Preparar petición a Moodle
        payload = {
            "wstoken": MOODLE_TOKEN,
            "wsfunction": "core_course_get_courses_by_field",
            "moodlewsrestformat": "json",
            "field": moodle_field,
            "value": valor
        }

        url = f"{MOODLE_URL}/webservice/rest/server.php"
        response = requests.post(url, params=payload)

        if response.ok:
            cursos = response.json().get("courses", [])

            return [
                {
                    ASIGNATURA_ID: curso.get("id"),
                    ASIGNATURA_NOMBRE: curso.get("fullname"),
                    ASIGNATURA_NOMBRE_CORTO: curso.get("shortname"),
                }
                for curso in cursos
            ]
        else:
            logging.getLogger("moodle").error(
                f"Error al consultar Moodle: {response.status_code} - {response.text}"
            )
            return None

    except Exception as e:
        logging.getLogger("moodle").error(f"Error al obtener asignatura(s) desde Moodle: {e}")
        return None



##===========================
## ===== Grupos_tutoria =====
##===========================

def create_grupo_tutoria(usuario_id, nombre, tipo, asignatura_id, chat_id = None, enlace_invitacion = None, do_commit=True):
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

def update_grupo_tutoria(grupo_id, do_commit=True, **kwargs):
    """Actualiza los datos de una grupo de tutoría"""
    if not all(k in GRUPO_CAMPOS_VALIDOS for k in kwargs):
        raise ValueError("Campo inválido en la actualización del grupo de tutoría")

    try:
        query = f"UPDATE {GRUPOS} SET "
        query += ", ".join([f"{GRUPO_FIELDS[k]} = {PLACEHOLDER}" for k in kwargs])
        query += f" WHERE {GRUPO_ID} = {PLACEHOLDER}"
                
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
    """
    Devuelve grupos de tutoría desde la BD local, enriquecidos con:
    - Nombre de la asignatura desde Moodle (fullname)
    - Nombre y apellidos del profesor desde Moodle (firstname + lastname)
    """
    try:
        if not all(k in GRUPO_CAMPOS_VALIDOS for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Grupos_tutoria")

        # Consulta local básica
        query = f"""SELECT * FROM {GRUPOS} WHERE 1=1"""

        for k in kwargs:
            query += f" AND {GRUPO_FIELDS[k]} = {PLACEHOLDER}"

        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()))
        rows = cursor.fetchall()

        result = []
        for row in rows:
            result.append(dict(row))

        return result

    except Exception as e:
        logging.getLogger('db.queries').error(f"Error al obtener grupo de tutoría: {e}")
        rollback()
        return None

    

##=======================
## ===== Matriculas =====
##=======================

def get_matriculas_asignatura_de_usuario(**kwargs):
    """
    Devuelve lista de dicts con: usuario_id, asignatura_id, matricula_tipo y nombre de la asignatura.
    Filtra por: usuario_id, asignatura_id, y/o rol.
    """
    try:
        usuario_id = kwargs.get("MATRICULA_ID_USUARIO")
        asignatura_id = kwargs.get("MATRICULA_ID_ASIGNATURA")
        rol = kwargs.get("MATRICULA_TIPO")  # Ej: "editingteacher", "student", etc.

        if not (usuario_id or asignatura_id):
            raise ValueError("Se requiere al menos 'usuario_id' o 'asignatura_id'")

        url = f"{MOODLE_URL}/webservice/rest/server.php"
        token = MOODLE_TOKEN

        results = []

        # --- Caso: buscar por usuario ---
        if usuario_id:
            usuario_busqueda_local = get_usuarios_local(USUARIO_ID=usuario_id)
            if not usuario_busqueda_local or usuario_busqueda_local == []:
                return []
            usuario_busqueda_local = usuario_busqueda_local[0]
            payload = {
                "wstoken": token,
                "wsfunction": "core_enrol_get_users_courses",
                "moodlewsrestformat": "json",
                "userid": usuario_busqueda_local[USUARIO_ID_MOODLE],
            }
            resp = requests.post(url, params=payload)
            if not resp.ok:
                raise Exception(f"Error al consultar cursos del usuario: {resp.text}")
            cursos = resp.json()

            for curso in cursos:
                course_id = curso["id"]
                course_name = curso.get("fullname", "Desconocido")
                course_shortname = curso.get("shortname", "Desconocido")

                # Si se especifica asignatura_id y no coincide, se omite
                if asignatura_id and course_id != asignatura_id:
                    continue
                
                if rol:
                    # Obtener usuarios de ese curso para verificar el rol
                    payload_users = {
                        "wstoken": token,
                        "wsfunction": "core_enrol_get_enrolled_users",
                        "moodlewsrestformat": "json",
                        "courseid": course_id,
                    }
                    resp_users = requests.post(url, params=payload_users)
                    if not resp_users.ok:
                        raise Exception(f"Error al consultar usuarios del curso {course_id}: {resp_users.text}")
                    usuarios = resp_users.json()

                    for user in usuarios:
                        user_local = get_usuarios_local(USUARIO_ID_MOODLE=user['id'])
                        if not user_local or user_local == []:
                            continue
                        user_local = user_local[0]
                        if user["id"] != usuario_busqueda_local[USUARIO_ID_MOODLE] and (not rol or rol != MATRICULA_TODAS):
                            continue
                        roles = [r["shortname"] for r in user.get("roles", [])]
                        if rol and rol != MATRICULA_TODAS and rol not in roles:
                            continue
                        results.append({
                            MATRICULA_ID_USUARIO: user_local[USUARIO_ID],
                            MATRICULA_ID_MOODLE: user["id"],
                            MATRICULA_ID_ASIGNATURA: course_id,
                            MATRICULA_TIPO: MATRICULA_PROFESOR if roles and MATRICULA_PROFESOR in roles else MATRICULA_ESTUDIANTE,
                            MATRICULA_ASIGNATURA_NOMBRE: course_name,
                            MATRICULA_ASIGNATURA_NOMBRE_CORTO: course_shortname,
                            MATRICULA_USUARIO_NOMBRE: user.get("firstname", "Desconocido"),
                            MATRICULA_USUARIO_APELLIDOS: user.get("lastname", "Desconocido"),
                            MATRICULA_USUARIO_EMAIL: user.get("email", "Desconocido"),
                        })
                else:
                    # Si no se especifica rol, no conocemos el tipo de matrícula
                    results.append({
                        MATRICULA_ID_USUARIO: usuario_id,
                        MATRICULA_ID_MOODLE: usuario_busqueda_local[USUARIO_ID_MOODLE],
                        MATRICULA_ID_ASIGNATURA: course_id,
                        MATRICULA_TIPO: "No obtenido",  # No se especifica tipo
                        MATRICULA_ASIGNATURA_NOMBRE: course_name,
                        MATRICULA_ASIGNATURA_NOMBRE_CORTO: course_shortname,
                        MATRICULA_USUARIO_NOMBRE: "No obtenido",
                        MATRICULA_USUARIO_APELLIDOS: "No obtenido",
                        MATRICULA_USUARIO_EMAIL: "No obtenido",
                    })

        # --- Caso: buscar por curso ---
        elif asignatura_id:
            payload = {
                "wstoken": token,
                "wsfunction": "core_enrol_get_enrolled_users",
                "moodlewsrestformat": "json",
                "courseid": asignatura_id,
            }
            resp = requests.post(url, params=payload)
            if not resp.ok:
                raise Exception(f"Error al consultar usuarios del curso: {resp.text}")
            
            usuarios = resp.json()

            for user in usuarios:
                usuario_busqueda_local = get_usuarios_local(USUARIO_ID_MOODLE=user["id"])
                if not usuario_busqueda_local or usuario_busqueda_local == []:
                    continue
                usuario_busqueda_local = usuario_busqueda_local[0]
                if usuario_id and usuario_busqueda_local[USUARIO_ID] != usuario_id:
                    continue
                roles = [r["shortname"] for r in user.get("roles", [])]
                if rol and rol != MATRICULA_TODAS and rol not in roles:
                    continue
                results.append({
                    MATRICULA_ID_USUARIO: usuario_busqueda_local[USUARIO_ID],
                    MATRICULA_ID_MOODLE: user["id"],
                    MATRICULA_ID_ASIGNATURA: asignatura_id,
                    MATRICULA_TIPO: MATRICULA_PROFESOR if roles and MATRICULA_PROFESOR in roles else MATRICULA_ESTUDIANTE,
                    MATRICULA_ASIGNATURA_NOMBRE: "No obtenido",
                    MATRICULA_ASIGNATURA_NOMBRE_CORTO: "No obtenido",
                    MATRICULA_USUARIO_NOMBRE: user.get("firstname", "Desconocido"),
                    MATRICULA_USUARIO_APELLIDOS: user.get("lastname", "Desconocido"),
                    MATRICULA_USUARIO_EMAIL: user.get("email", "No especificado"),
                })
        return results

    except Exception as e:
        logging.getLogger('moodle').error(f"Error en get_matriculas_moodle: {e}")
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



##=======================
## ===== Reacciones =====
##=======================
    

def insert_reaccion(profesor_id, alumno_id, asignatura_id, emoji, cantidad, do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(
            f"""INSERT INTO {REACCIONES} 
                ({REACCION_ID_PROFESOR}, {REACCION_ID_ALUMNO}, {REACCION_ID_ASIGNATURA}, {REACCION_EMOJI}, {REACCION_CANTIDAD}) 
                VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})""",
            (profesor_id, alumno_id,asignatura_id, emoji, cantidad)
        )
        if do_commit:
            commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al crear reacción: {e}")
        rollback()
        return None

def update_reaccion(reaccion_id, do_commit=True, **kwargs):
    """Actualiza los datos de una reacción"""
    if not all(k in REACCION_CAMPOS_VALIDOS for k in kwargs):
        raise ValueError("Campo inválido en la actualización de reacción")

    try:
        query = f"UPDATE {REACCIONES} SET "
        query += ", ".join([f"{REACCION_FIELDS[k]} = {PLACEHOLDER}" for k in kwargs])
        query += f" WHERE {REACCION_ID} = {PLACEHOLDER}"

        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()) + [reaccion_id])
        if do_commit:
            commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error al actualizar reacción: {e}")
        rollback()
        return False

def delete_reaccion(reaccion_id, do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(f"DELETE FROM {REACCIONES} WHERE {REACCION_ID} = {PLACEHOLDER}", (reaccion_id,))
        if do_commit:
            commit()
    except Exception as e:
        print(f"Error al eliminar reacción: {e}")
        rollback()

def get_reacciones(**kwargs):
    try:
        if not all(k in REACCION_CAMPOS_VALIDOS for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de reacciones")

        query = f"SELECT * FROM {REACCIONES} WHERE 1=1"
        for k in kwargs:
            query += f" AND {REACCION_FIELDS[k]} = {PLACEHOLDER}"

        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error al obtener reacción(es): {e}")
        rollback()
        return None
    


##=====================
## ===== Mensajes =====
##=====================


def insert_mensaje(telegram_id, chat_id, sender_id, profesor_id, asignatura_id, texto, do_commit=True):
    cursor = get_cursor()
    try:
        cursor.execute(
            f"""INSERT INTO {MENSAJES} 
            ({MENSAJE_ID_TELEGRAM}, {MENSAJE_ID_CHAT}, {MENSAJE_ID_SENDER}, 
             {MENSAJE_ID_PROFESOR}, {MENSAJE_ID_ASIGNATURA}, {MENSAJE_TEXTO}) 
            VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})""",
            (telegram_id, chat_id, sender_id, profesor_id, asignatura_id, texto)
        )
        if do_commit:
            commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error al insertar mensaje: {e}")
        rollback()
        return None

# No se usa
def update_mensaje(mensaje_id, do_commit=True, **kwargs):
    if not all(k in MENSAJE_CAMPOS_VALIDOS for k in kwargs):
        raise ValueError("Campo inválido en la actualización de mensaje")

    try:
        query = f"UPDATE {MENSAJES} SET "
        query += ", ".join([f"{MENSAJE_FIELDS[k]} = {PLACEHOLDER}" for k in kwargs])
        query += f" WHERE {MENSAJE_ID} = {PLACEHOLDER}"

        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()) + [mensaje_id])
        if do_commit:
            commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Error al actualizar mensaje: {e}")
        rollback()
        return False

# No se usa
def delete_mensaje(mensaje_id):
    cursor = get_cursor()
    try:
        cursor.execute(f"DELETE FROM {MENSAJES} WHERE {MENSAJE_ID} = {PLACEHOLDER}", (mensaje_id,))
        commit()
    except Exception as e:
        print(f"Error al eliminar mensaje: {e}")
        rollback()

def get_mensajes(**kwargs):
    try:
        if not all(k in MENSAJE_CAMPOS_VALIDOS for k in kwargs):
            raise ValueError("Campo inválido en búsqueda de Mensajes")

        query = f"SELECT * FROM {MENSAJES} WHERE 1=1"
        for k in kwargs:
            query += f" AND {MENSAJE_FIELDS[k]} = {PLACEHOLDER}"

        cursor = get_cursor()
        cursor.execute(query, list(kwargs.values()))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error al obtener mensaje(s): {e}")
        rollback()
        return None
