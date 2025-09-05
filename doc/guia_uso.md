# <u>Guia de uso</u>

## <u>- Comandos generales</u>

### · Registro

Iniciar el proceso de registro

Si se realiza en una nueva cuenta de telegram se desvinculara la anterior.
Si ya se esta registrado se reasignara el menu de comandos

- Hacer /start en el bot principal
- Introducir tu email (@correo.ugr.es para alumnos y @ugr.es para profesores)
- Introducir codigo de verificación recibido en el email

### · Help

Muestra los comandos disponibles

- Hacer /help

## <u>- Alumnos</u>

### · Tutoria

Muestra informacion sobre los metodos de comunicación con profesores y permite solicitar tutoria privada

- Hacer /tutoria
- Se muestran 2 mensajes por cada profesor de las asignaturas matriculadas. Uno con horarios y grupos de cada asignatura y uno para solicitar tutoria privada
- Si se quiere acceder a un grupo general hacer click en el enlace de la asignatura en el mensaje de profesor correspondoente
- Si se quiere solicitar tutoria pulsar el boton del profesor correspondiente y esperar a aceptacion/rechazo para recibir el enlace

### · Valorar profesor

Permite hacer un valoracion de profesores

- Hacer /valorar_profesor
- Seleccionar profesor a valorar
- Si ya se ha valorado indicar si quiere sobreescribir valoración (si no se cancela)
- Seleccionar puntuación
- Seleccionar si se quiere añadir comentario o no (si se quiere intrioducir comentario despues)
- Seleccionar si se quiere que sea anonima o no

### · Ver reacciones

Muestra reacciones recibidas de cada profesor en cada asignatura

- Hacer /ver_reacciones

### · Ver datos personales

Muestra tus datos personales

- Hacer /ver_misdatos

## <u>- Profesores</u>

### · Responder peticiones tutoria

Durante horarios indicados se puede recibir un mensaje pidiendo tutoria privada.

Si ya hay alguien en la sala de tutorias se le notificara de que alguien ha pedido pero esta ocupada.
Si esto no deberia ser vaya al grupo de tutorias y haga /finalizar o pulse el boton.

- Al pulsar aceptar se le enviara al alumno el enlace de invitación temporal al grupo de tutorias creado previamente.
- Al pulsar rechazar se le notificara al alumno

### · Ver datos personales

Muestra tus datos personales y grupos creados y permite gestionarlos

- Hacer /ver_misdatos
- Seleccionar el grupo que se quiera gestionar si se desea
- Seleccionar opcion de gestion (eliminar solamente)

### · Crear grupo tutoria

Muestra tutorial de como crear grupos en el sistema, tambien da acceso a un faq y gestion de grupos

- Hacer /crear_grupo_tutoria
- Seguir tutorial de creacion de grupos
    - Crear grupo
    - Invitar al bot de grupos como administrador
    - Hacer /configurar_grupo
    - Seleccionar asignatura del grupo
- Puede ver el FAQ mediante un botón
- Puede acceder a gestion de grupos como en /ver_misdatos con el otro botón

### · Configurar Horario

Permite la modificación de horarios en los que se pueden recibir tutorias

- Hacer /configurar_horario
- Seleccionar dia
- Añadir/eliminar franja
    - Para añadir introducir franja con formato XX:XX-XX:XX
    - Para eliminar seleccionar franja a eliminar
- Una vez realizados los cambios deseados guardar

### · Ver reacciones

Permite ver listado reacciones dadas a mensajes de alumnos en cada asignatura (posibilidad de usarse como medida de participación en la asignatura)

- Hacer /ver_reacciones
- Parece listado segun asignatura y alumno con la cantidad de cada reacción recibida

### · Ver valoraciones

Permite ver meda de las valoraciones recibidas, mensajes recibidos y nombres asociados a valoraciones no anonimas

- Hacer /ver_valoraciones
- Pulsar boton de lo que se quiera ver

### · Ver mensajes

Permite obtener un xml con un listado de todos los mensajes enviados en chats de la asignatura seleccionada

- Hacer /ver_mensajes
- Seleccionar asignatura
- Descargar archivo

## <u>- Acciones en grupos</u>

### · Finalizar tutoria

Acabar la tutoria permitiendo que otras personas puedan solicitar otra tutoria privada y expulsando al estudiante actual.

Esto puede ocurrir de 3 formas

- Pulsando el boton de finalizar tutoria (en escritoria puede esconderse un un menu que se abre pulsando el botón de dado)
- Haciendo /finalizar
- Si el alumno se sale manualmente del grupo

<span style="color: red;">¡¡¡NO EXPULSE AL ALUMNO DIRECTAMENTE YA QUE USTED ES ADMINISTRADOR LO CUAL HACER QUE NO PUDIERA ENTRAR DE NUEVO A NO SER QUE LO REVOQUE!!!</span>

### · Configurar grupo (Profesores)

Permite añadir un grupo al sistema

- Añadir al bot como administrador
- Hacer /configurar_grupo
- Seleccionar asignatura
