PLACEHOLDER = f"%s"

##=====================
## ===== Usuarios =====
##=====================

USUARIOS = "Usuarios"

# Constantes de campos válidos en la base de datos
USUARIO_ID = "Usuario_id"
USUARIO_NOMBRE = "Nombre"
USUARIO_APELLIDOS = "Apellidos"
USUARIO_TIPO = "Tipo"
USUARIO_EMAIL = "Email_UGR"
USUARIO_ID_TELEGRAM = "TelegramID"
USUARIO_HORARIO = "Horario"

# Conjunto de campos válidos (para validación rápida)
USUARIO_CAMPOS_VALIDOS = {
    "USUARIO_ID",
    "USUARIO_NOMBRE",
    "USUARIO_APELLIDOS",
    "USUARIO_TIPO",
    "USUARIO_EMAIL",
    "USUARIO_ID_TELEGRAM",
    "USUARIO_HORARIO",
}

USUARIO_FIELDS = {
    "USUARIO_ID":USUARIO_ID,
    "USUARIO_NOMBRE":USUARIO_NOMBRE,
    "USUARIO_APELLIDOS":USUARIO_APELLIDOS,
    "USUARIO_TIPO":USUARIO_TIPO,
    "USUARIO_EMAIL":USUARIO_EMAIL,
    "USUARIO_ID_TELEGRAM":USUARIO_ID_TELEGRAM,
    "USUARIO_HORARIO":USUARIO_HORARIO,
}

# Posibles valores campos
USUARIO_TIPO_PROFESOR = "profesor"
USUARIO_TIPO_ESTUDIANTE = "estudiante"



##========================
## ===== Asignaturas =====
##========================

ASIGNATURAS = "Asignaturas"

# Constantes de campos de la tabla ASIGNATURAS
ASIGNATURA_ID = "Asignatura_id"
ASIGNATURA_NOMBRE = "Nombre"

# Conjunto de campos válidos (para validación)
ASIGNATURA_CAMPOS_VALIDOS = {
    "ASIGNATURA_ID",
    "ASIGNATURA_NOMBRE",
}

ASIGNATURA_FIELDS = { 
    "ASIGNATURA_ID":ASIGNATURA_ID,
    "ASIGNATURA_NOMBRE":ASIGNATURA_NOMBRE,
}



##===========================
## ===== Grupos_tutoria =====
##===========================

GRUPOS = "Grupos_tutoria"

# Constantes de campos de la tabla GRUPOS o SALAS
GRUPO_ID = "Grupo_id"
GRUPO_ID_PROFESOR = "Profesor_id"
GRUPO_NOMBRE = "Nombre_grupo"
GRUPO_TIPO = "Tipo_grupo"
GRUPO_ID_ASIGNATURA = "Asignatura_id"
GRUPO_ID_CHAT = "Chat_id"
GRUPO_ENLACE = "Enlace_invitacion"
GRUPO_PROFESOR = "Profesor"
GRUPO_ASIGNATURA = "Asignatura"
GRUPO_FECHA = "Fecha_creacion"
GRUPO_EN_USO = "En_uso"

# Conjunto de campos válidos para validación
GRUPO_CAMPOS_VALIDOS = {
    "GRUPO_ID",
    "GRUPO_ID_PROFESOR",
    "GRUPO_NOMBRE",
    "GRUPO_TIPO",
    "GRUPO_ID_ASIGNATURA",
    "GRUPO_ID_CHAT",
    "GRUPO_ENLACE",
    "GRUPO_EN_USO",
}

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

# Posibles valores campos
GRUPO_PUBLICO = "pública"
GRUPO_PRIVADO = "privada"



##=======================
## ===== Matriculas =====
##=======================

MATRICULAS = "Matriculas"

# Constantes de campos de la tabla MATRICULAS
MATRICULA_ID = "Matricula_id"
MATRICULA_ID_USUARIO = "Usuario_id"
MATRICULA_ID_ASIGNATURA = "Asignatura_id"
MATRICULA_TIPO = "Tipo"
MATRICULA_ASIGNATURA= "Asignatura"
MATRICULA_CODIGO= "Codigo"
MATRICULA_CARRERA= "Carrera"

# Conjunto de campos válidos para validación
MATRICULA_CAMPOS_VALIDOS = {
    "MATRICULA_ID",
    "MATRICULA_ID_USUARIO",
    "MATRICULA_ID_ASIGNATURA",
    "MATRICULA_TIPO",
}

MATRICULA_FIELDS = {           
    "MATRICULA_ID":MATRICULA_ID,
    "MATRICULA_ID_USUARIO":MATRICULA_ID_USUARIO,
    "MATRICULA_ID_ASIGNATURA":MATRICULA_ID_ASIGNATURA,
    "MATRICULA_TIPO":MATRICULA_TIPO,
}

# Posibles valores campos
MATRICULA_ESTUDIANTE = "estudiante"
MATRICULA_PROFESOR = "docente"



##=========================
## ===== Valoraciones =====
##=========================

VALORACIONES = "Valoraciones"

# Constantes de campos de la tabla VALORACIONES
VALORACION_ID = "Valoracion_id"
VALORACION_ID_EVALUADOR = "Evaluador_id"
VALORACION_ID_PROFESOR = "Profesor_id"
VALORACION_PUNTUACION = "Puntuacion"
VALORACION_COMENTARIO = "Comentario"
VALORACION_FECHA = "Fecha"
VALORACION_ANONIMA = "Anonimo"

# Conjunto de campos válidos (para validación)
VALORACION_CAMPOS_VALIDOS = {
    "VALORACION_ID",
    "VALORACION_ID_EVALUADOR",
    "VALORACION_ID_PROFESOR",
    "VALORACION_PUNTUACION",
    "VALORACION_COMENTARIO",
    "VALORACION_FECHA",
    "VALORACION_ANONIMA",
}

VALORACION_FIELDS = { 
    "VALORACION_ID":VALORACION_ID,
    "VALORACION_ID_EVALUADOR":VALORACION_ID_EVALUADOR,
    "VALORACION_ID_PROFESOR":VALORACION_ID_PROFESOR,
    "VALORACION_PUNTUACION":VALORACION_PUNTUACION,
    "VALORACION_COMENTARIO":VALORACION_COMENTARIO,
    "VALORACION_FECHA":VALORACION_FECHA,
    "VALORACION_ANONIMA":VALORACION_ANONIMA,
}

# Posibles valores campos
VALORACION_SI_ANONIMA = True
VALORACION_NO_ANONIMA = False