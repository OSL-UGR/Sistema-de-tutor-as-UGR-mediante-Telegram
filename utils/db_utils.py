# db_utils.py
from db.queries import (
    get_carreras,
    get_matriculas,
    get_usuarios,
    insert_carrera,
    insert_matricula,
    update_matricula,
    rollback
)

def crear_o_actualizar_matricula(user_id, asignatura_id, tipo_usuario=None, curso="Actual"):
    """
    Crea o actualiza una matrícula para un usuario en una asignatura

    Args:
        user_id: ID del usuario
        asignatura_id: ID de la asignatura
        tipo_usuario: Tipo de usuario para esta matrícula (opcional)
        curso: Curso académico (opcional)

    Returns:
        int: ID de la matrícula creada o actualizada, o None si hubo error
    """
    try:
        # Verificar si ya existe la matrícula
        matricula = get_matriculas(Id_ususario=user_id, Id_asignatura=asignatura_id)

        if not matricula:
            # Si no se proporciona tipo, obtenerlo del usuario
            if tipo_usuario is None:
                user = get_usuarios(Id_usuario=user_id)
                if user:
                    tipo_usuario = user.get("Tipo", "estudiante")  # por defecto 'estudiante'

            # Insertar matrícula con método tuyo
            return insert_matricula(Id_usuario=user_id, Id_asignatura=asignatura_id, Tipo=tipo_usuario, Curso=curso)

        else:
            # Ya existe: actualizar si hay cambios
            matricula_id = matricula["id_matricula"]
            updates = {}
            if tipo_usuario is not None and tipo_usuario != matricula.get("Tipo"):
                updates["Tipo"] = tipo_usuario
            if curso != "Actual" and curso != matricula.get("Curso"):
                updates["Curso"] = curso

            if updates:
                success = update_matricula(matricula_id, **updates)
                if not success:
                    rollback()
                    return None

            return matricula_id

    except Exception as e:
        import logging
        logging.getLogger("db.queries").error(f"Error al crear matrícula: {e}")
        rollback()
        return None

def verificar_disponibilidad_profesor(profesor_id):
    """
    Verifica si un profesor está disponible actualmente según su horario almacenado en el campo 'Horario' del usuario
    """
    from handlers.tutorias import verificar_horario_tutoria
    
    try:
        usuario = get_usuarios(Id_usuario=profesor_id)
        if not usuario:
            return False
        
        horario = usuario.get("Horario")
        if not horario:
            return False
        
        disponible = verificar_horario_tutoria(horario)
        return disponible
    
    except Exception as e:
        import logging
        logging.getLogger("db.queries").error(f"Error al verificar disponibilidad del profesor {profesor_id}: {e}")
        return False


def get_or_insert_carrera(nombre_carrera):
    """Obtiene una carrera por nombre o la crea si no existe"""
    if not nombre_carrera or nombre_carrera.strip() == '':
        return None  # No crear carreras vacías

    try:
        carrera = get_carreras(Nombre_carrera=nombre_carrera)
        if carrera:
            return carrera["id_carrera"]
        else:
            carrera_id = insert_carrera(Nombre_carrera=nombre_carrera)
            return carrera_id
    except Exception as e:
        print(f"Error al obtener/crear carrera: {e}")
        rollback()
        return None
