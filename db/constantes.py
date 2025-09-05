PLACEHOLDER = f"%s"

##=====================
## ===== Usuarios =====
##=====================

USUARIOS = "Usuarios"

# Constantes de campos válidos en la base de datos
USUARIO_ID = "id"
USUARIO_ID_MOODLE = "moodle_id"
USUARIO_TIPO = "tipo"
USUARIO_NOMBRE = "firstname"
USUARIO_APELLIDOS = "lastname"
USUARIO_EMAIL = "email"
USUARIO_ID_TELEGRAM = "telegram_id"
USUARIO_HORARIO = "horario"

USUARIO_FIELDS = {
    "USUARIO_ID":USUARIO_ID,
    "USUARIO_ID_MOODLE": USUARIO_ID_MOODLE,
    "USUARIO_TIPO":USUARIO_TIPO,
    "USUARIO_NOMBRE":USUARIO_NOMBRE,
    "USUARIO_APELLIDOS":USUARIO_APELLIDOS,
    "USUARIO_EMAIL":USUARIO_EMAIL,
    "USUARIO_ID_TELEGRAM":USUARIO_ID_TELEGRAM,
    "USUARIO_HORARIO":USUARIO_HORARIO,
}

USUARIO_CAMPOS_VALIDOS = set(USUARIO_FIELDS.keys())

# Posibles valores campos
USUARIO_TIPO_PROFESOR = "editingteacher"
USUARIO_TIPO_ESTUDIANTE = "student"



##========================
## ===== Asignaturas =====
##========================

ASIGNATURA_ID = "id"
ASIGNATURA_NOMBRE = "fullname"
ASIGNATURA_NOMBRE_CORTO = "shortname"

ASIGNATURA_FIELDS = {
    "ASIGNATURA_ID": ASIGNATURA_ID,
    "ASIGNATURA_NOMBRE": ASIGNATURA_NOMBRE,
    "ASIGNATURA_NOMBRE_CORTO": ASIGNATURA_NOMBRE_CORTO,
}

ASIGNATURA_CAMPOS_VALIDOS = set(ASIGNATURA_FIELDS.keys())



##===========================
## ===== Grupos_tutoria =====
##===========================

GRUPOS = "Grupos_tutoria"

# Constantes de campos de la tabla GRUPOS o SALAS
GRUPO_ID = "grupo_id"
GRUPO_ID_PROFESOR = "profesor_id"
GRUPO_NOMBRE = "nombre_grupo"
GRUPO_TIPO = "tipo_grupo"
GRUPO_ID_ASIGNATURA = "asignatura_id"
GRUPO_ID_CHAT = "chat_id"
GRUPO_ENLACE = "enlace_invitacion"
GRUPO_FECHA = "fecha_creacion"
GRUPO_EN_USO = "en_uso"

GRUPO_FIELDS = {           
    "GRUPO_ID":GRUPO_ID,
    "GRUPO_ID_PROFESOR":GRUPO_ID_PROFESOR,
    "GRUPO_NOMBRE":GRUPO_NOMBRE,
    "GRUPO_TIPO":GRUPO_TIPO,
    "GRUPO_ID_ASIGNATURA":GRUPO_ID_ASIGNATURA,
    "GRUPO_ID_CHAT":GRUPO_ID_CHAT,
    "GRUPO_ENLACE":GRUPO_ENLACE,
    "GRUPO_EN_USO":GRUPO_EN_USO
}

# Conjunto de campos válidos para validación
GRUPO_CAMPOS_VALIDOS = set(GRUPO_FIELDS.keys())

# Posibles valores campos
GRUPO_PUBLICO = "público"
GRUPO_PRIVADO = "privado"



##=======================
## ===== Matriculas =====
##=======================

MATRICULAS = "Matriculas"

# Constantes de campos de la tabla MATRICULAS
MATRICULA_ID_USUARIO = "id"
MATRICULA_ID_MOODLE = "userid"
MATRICULA_ID_ASIGNATURA = "courseid"
MATRICULA_TIPO = "tipo"
MATRICULA_ASIGNATURA_NOMBRE= "asignatura_nombre"
MATRICULA_ASIGNATURA_NOMBRE_CORTO = "asignatura_nombre_corto"
MATRICULA_USUARIO_NOMBRE = "nombre"
MATRICULA_USUARIO_APELLIDOS = "apellidos"
MATRICULA_USUARIO_EMAIL = "email"

MATRICULA_FIELDS = {           
    "MATRICULA_ID_USUARIO":MATRICULA_ID_USUARIO,
    "MATRICULA_ID_MOODLE": MATRICULA_ID_MOODLE,
    "MATRICULA_ID_ASIGNATURA":MATRICULA_ID_ASIGNATURA,
    "MATRICULA_TIPO":MATRICULA_TIPO,
    "MATRICULA_ASIGNATURA_NOMBRE": MATRICULA_ASIGNATURA_NOMBRE,
    "MATRICULA_ASIGNATURA_NOMBRE_CORTO": MATRICULA_ASIGNATURA_NOMBRE_CORTO,
    "MATRICULA_USUARIO_NOMBRE": MATRICULA_USUARIO_NOMBRE,
    "MATRICULA_USUARIO_APELLIDOS": MATRICULA_USUARIO_APELLIDOS,
    "MATRICULA_USUARIO_EMAIL": MATRICULA_USUARIO_EMAIL,
}

# Conjunto de campos válidos para validación
MATRICULA_CAMPOS_VALIDOS = set(MATRICULA_FIELDS.keys())

# Posibles valores campos
MATRICULA_ESTUDIANTE = "student"
MATRICULA_PROFESOR = "editingteacher"
MATRICULA_TODAS = "todas"  # Para obtener todas las matrículas, tanto de estudiantes como de profesores



##=========================
## ===== Valoraciones =====
##=========================

VALORACIONES = "Valoraciones"

# Constantes de campos de la tabla VALORACIONES
VALORACION_ID = "valoracion_id"
VALORACION_ID_EVALUADOR = "evaluador_id"
VALORACION_ID_PROFESOR = "profesor_id"
VALORACION_PUNTUACION = "puntuacion"
VALORACION_COMENTARIO = "comentario"
VALORACION_FECHA = "fecha"
VALORACION_ANONIMA = "anonimo"

VALORACION_FIELDS = { 
    "VALORACION_ID":VALORACION_ID,
    "VALORACION_ID_EVALUADOR":VALORACION_ID_EVALUADOR,
    "VALORACION_ID_PROFESOR":VALORACION_ID_PROFESOR,
    "VALORACION_PUNTUACION":VALORACION_PUNTUACION,
    "VALORACION_COMENTARIO":VALORACION_COMENTARIO,
    "VALORACION_FECHA":VALORACION_FECHA,
    "VALORACION_ANONIMA":VALORACION_ANONIMA,
}

# Conjunto de campos válidos (para validación)
VALORACION_CAMPOS_VALIDOS = set(VALORACION_FIELDS.keys())

# Posibles valores campos
VALORACION_SI_ANONIMA = True
VALORACION_NO_ANONIMA = False

##=======================
## ===== Reacciones =====
##=======================

REACCIONES = "Reacciones"

REACCION_ID = "reaccion_id"
REACCION_ID_PROFESOR = "profesor_id"
REACCION_ID_ALUMNO = "alumno_id"
REACCION_ID_ASIGNATURA = "asignatura_id"
REACCION_EMOJI = "emoji"
REACCION_CANTIDAD = "cantidad"

REACCION_FIELDS = {                                   
    "REACCION_ID":REACCION_ID,
    "REACCION_ID_PROFESOR":REACCION_ID_PROFESOR,
    "REACCION_ID_ALUMNO":REACCION_ID_ALUMNO,
    "REACCION_ID_ASIGNATURA":REACCION_ID_ASIGNATURA,
    "REACCION_EMOJI":REACCION_EMOJI,
    "REACCION_CANTIDAD":REACCION_CANTIDAD,
}

REACCION_CAMPOS_VALIDOS = set(REACCION_FIELDS.keys())



##=====================
## ===== Mensajes =====
##=====================


MENSAJES = "Mensajes"

MENSAJE_ID = "mensaje_id"
MENSAJE_ID_TELEGRAM = "telegram_id"
MENSAJE_ID_CHAT = "chat_id"
MENSAJE_ID_SENDER = "sender_id"
MENSAJE_ID_PROFESOR = "profesor_id"
MENSAJE_ID_ASIGNATURA = "asignatura_id"
MENSAJE_TEXTO = "texto"
MENSAJE_FECHA = "fecha"

MENSAJE_FIELDS = {
    "MENSAJE_ID": MENSAJE_ID,
    "MENSAJE_ID_TELEGRAM": MENSAJE_ID_TELEGRAM,
    "MENSAJE_ID_CHAT": MENSAJE_ID_CHAT,
    "MENSAJE_ID_SENDER": MENSAJE_ID_SENDER,
    "MENSAJE_ID_PROFESOR": MENSAJE_ID_PROFESOR,
    "MENSAJE_ID_ASIGNATURA": MENSAJE_ID_ASIGNATURA,
    "MENSAJE_TEXTO": MENSAJE_TEXTO,
    "MENSAJE_FECHA": MENSAJE_FECHA,
}

MENSAJE_CAMPOS_VALIDOS = set(MENSAJE_FIELDS.keys())



