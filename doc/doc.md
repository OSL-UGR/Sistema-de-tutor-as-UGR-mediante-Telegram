# <u>Documentación basica</u>

## <u>Estructura de carpetas:</u>

```
project
│   README.md
|   datos.env.example - Template de variables de entorno a rellenar
│   config.py - Codigo cargando las variables de entorno. Contiene comportamiento de comandos basicos (/start y /help)
|   main.py - Archivo main del bot principal. Contiene comportamiendo de comandos basicos (/help y /ver_misdatos inicial)
|   main_grupo.py - Archivo main del bot de grupos
|   requirements.txt - Lista de dependencias
│
└───db
│   │   __init__.py - Creacion de la conexión unica a la BD
│   │   constantes.py - Definicion de constantes
|   |   queries.py - Codigo de peticiones a la DB y API de moodle (estructura heredada de anterior version con exclusivamente una BD)
|   |   schema.sql - Schema de la BD a usar
│   
└───handlers - Definicion de respuesta a eventos de telegram del bot principal
|   │   commands.py - Definicion constantes de comandos
|   │   grupos.py - Reacciones a peticiones de información/creación/edición/eliminación de grupos de telegram (/crear_grupo_tutoria y
                    modificación de grupos en /ver_misdatos)
|   │   horarios.py - Reacciones relacionadas con la configuración de los horarios de tutorias de los profesores (/configurar_horario)
|   │   mensajes.py - Reacciones a peticions de ver historial de mensajes o reacciones (/ver_mensajes y /ver_reacciones)
|   │   registro.py - Reacciones a todo el proceso de registro de un nuevo usuario en el sistema y configuracion de sus comandos (/start)
|   │   tutorias.py - Reacciones relacionadas a todo el proceso de petición de tutorias y su aceptacion/rechazo por parte del profesor (/tutoria)
|   │   valoraciones.py - Reacciones relacionadas con el proceso de dar o ver valoraciones (/valorar_profesor y /ver_valoraciones)
|
└───handlers_grupo - Definicion de respuesta a eventos de telegram del bot de grupos
|   │   mensajes.py - Reacciones a nuevos mensajes y reacciones a mensajes
|   │   registro.py - Reacciones del proceso de regsitrar un grupo en el sistema (/configurar_grupo)
|   │   tutorias.py - Reacciones a eventos del menu de tutorias (actualmente solo acabar tutoria con el boton o /finalizar)
|   │   usuarios.py - Reacciones a eventos de usuarios (entra un usuario nuevo al grupo o sale por ejemplo)
|   │   utils.py - Funciones de utilidad del bot de grupos
|
└───doc
└───logs
└───tmp
└───utils
    │   state_manager.py - Metodos y arrays a usar para guardar información sobre el estado y datos de una conversacion
```
## <u>Aviso queries BD/MOODLE</u>

Originalmente este projecto tenia una base de datos propia donde se guardaban todos los datos. Al cambiar toda la base de datos y hacer que dependa
de moodle se adaptaron los metodos ya existentes a obtener la información pertinente de moodle. Debido a la diferencia de como se guardaban los datos
hay un metodo que es complicado de entender.

La mayoria de metodos son relativamente simples y siguen una de 3 formas:

- Metodos locales que solo hacen SQL basico (ej: pedir datos locales de un usuario para compobar si la id de telegram esta en el sistema)
- Obtener datos de la BD local y los pertinentes de moodle (ej: segun la id de telegram obtenemos id de moodle y de ahi su datos personales como nombre)
- Obtener datos de moodle segun un dato personal y de ahi los locales (ej: pedimos un usuario segun email, lo que pedimos a moodle y segun su id rellenamos datos locales correspondiente si existen (si no no estaria registrado))

Para utilizar los metodos get normales se especifican los campos por los que filtrar con las constantes definidas en db/constantes.py como argumentos

```
get_usuarios(USARIO_ID_TELEGRAM=id)
```

para update igual pero especificando la id del que modificar y usando las constantes para especificar los valores de los campos
```
update_reaccion(id, REACCION_CANTIDAD=cantidad)
```

</br><span style="color: red;">IMPORTANTE</span>

Sin embargo el metodo get_matriculas_asignatura_de_usuario una excepción que es un mas complicada debido a como funciona la API de moodle

En el caso de que filtres por usuario, primero obtenemos las asignaturas del usuario, pero asi no obtenemos roles, por lo que tenemos que volver a
hacer una peticion por cada asignatura matriculada para obtener los usuarios matriculados en esta, ya que si no no sabemos que rol tiene el usuario.
Por esto acabamos teniendo todas las matriculas de usuarios que comparten asignaturas con el que queremos. Para filtrar esto tenemos un parametro
extra que nos permite indicar lo que queremos, este seria el tipo de matricula. Los posibles valores son:

- None: Obtiene solo las asignaturas, sin obtener roles ni datos personales del alumno
- MATRICULA_ESTUDIANTE: Obtiene todos los datos pero filtra para devolver solamente las matriculas del estudiante especifico
- MATRICULA_PROFESOR: Obtienen todos los datos pero filtra para devolver solamente las matriculas de los profesores que imparten las asignaturas del alumno
- MATRICULA_TODAS: Devuelve toda la información

En el caso de filtrar segun la asignatura pero no segun usuario solamente obtenemos los datos de los alumnos y faltarian los datos de la asignatura como el nombre
ya que pedir eso necesitaria una query extra que añadiria tiempo de espera pero se puede hacer un get_asignatura si estos fueran necesarios, el resto es igual.

## <u>Como seguir las llamadas a telegram?</u>

Principalmente la interaccion de telegram empiezan con un comando por parte del usuarios el cual recibimos con:

    @bot.message_handler(commands=[COMMAND])

otra opcion seria que reaccionaramos a un evento como una reacción/entrada de una persona al grupo etc los ucales tienen sus propios nombres en el bot
como message_reaction_handler o chat_member_handler.

Cuando ya tenemos una interacción iniciada, si nuestro mensaje tiene componentes interactivos como botones, al pulsarse este recibiriamos un callback con los datos.
Un ejemplo de esto seria /ver_valoraciones donce podemos optar por ver los comentarios recibidos o nombres de las valoraciones no anonimas.

Esto se haria así:

```
markup.add(
            types.InlineKeyboardButton(
                "📝 Ver comentarios",
                callback_data=VER_COMENTARIOS
            ),
            types.InlineKeyboardButton(
                "🧑 Ver nombres",
                callback_data=VER_NO_ANONIMAS
            )
        )
```

y reaccionariamos a cada opcion de la sigiente forma

```
@bot.callback_query_handler(func=lambda call: call.data.startswith(VER_COMENTARIOS))
    def handle_ver_comentarios(call):
```

en el caso de que lo que se pida sea un mensaje y no opdamos recibirlo por callback estableceremos un estado mediante los metodos de utils/state_manager.py
y creariamos un metodo que solo si activa si la conversacion esta en ese estado de la siguiente forma:

    @bot.message_handler(func=lambda message: get_state(message.chat.id) == STATE_VERIFY_TOKEN)

Este ejemplo seria del estado de cuando estamos esperando un codigo de verificación de email para el registro de un usuario

Para mantener datos entre un paso y el siguiente (para hacer una valoracion tenemos que guardar el profesor al que corresponde, su puntuación, etc... por ej)
lo hacemos de 2 formas distintas:

- Tenemos los datos en el propio callback
```
callback_data=f"{ELIMINAR_FRANJA}{dia}_{franja}" 
```
```
a1, a2, dia, hora = call.data.split("_", 3)
```

- Lo guardamos en un diccionario global user_data[chat_id][campo] definido en state_manager

Hay un archivo donde guarda en un array propio heredado de una anterior version (handlers/tutorias.py)