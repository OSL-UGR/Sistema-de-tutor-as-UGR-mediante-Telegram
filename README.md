# 📚 Automatización de Tutorías Universitarias con Telegram Bot

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/) [![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## Instalación & Configuración

1. Clona el repositorio:

   ```bash
   git clone https://github.com/Velasco-A/Velasco-A-Sistema-de-mensajeria-para-tutorias-UGR.git
   cd Velasco-A-Sistema-de-mensajeria-para-tutorias-UGR
   ```

2. Crea y activa un entorno virtual:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .\.venv\Scripts\activate   # Windows
   ```

3. Instala dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Crea una base de datos con el charset utf8mb4:

   En mariaDB seria de la forma:

   ```sql
   CREATE DATABASE {DATABASE_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_bin
   ```

5. Crear un servicio externo en Moodle
   - En la admnistracion del sitio Moodle vaya a la sección de servicios externos y cree un nuevo servicio.
   - Añada al servicio los siguientes permisos que requiere la aplicación:
     - core_user_get_users
     - core_course_get_courses_by_field
     - core_enrol_get_users_courses
     - core_enrol_get_enrolled_users
   - Active la API REST para servicios web en la sección de gestion de protocolos.
   - Genera un token para el servicio.

6. Crea 2 bots de Telegram.
   - Inicia una comversación con @BotFather.
   - Crea 2 bots, uno para conversacion directa y otra para presencia en grupos.
   - Obten los tokens de ambos.

7. Configura variables de entorno copiando `datos.env.example` a `datos.env` y completando los valores.
Los datos de SMTP se usaran para enviar codigos de verificación a los usuarios.

8. Inicia los bots con:

   ```bash
   python3 main.py
   
   # o en 2 terminales
   python3 bot_principal.py
   python3 bot_grupos.py
   ```

---

## Uso

### Iniciar bot principal

```bash
python main.py
```

Envía `/start` en Telegram para comenzar el alta.

### Iniciar bot de grupos

```bash
python main_grupo.py
```

Agregar el bot como admin en un grupo para habilitar la configuración.

---

## Contribuir

1. Haz un fork.
2. Crea una rama: `git checkout -b feature/nombre`.
3. Haz commit: `git commit -m "Descripción"`.
4. Push: `git push origin feature/nombre`.
5. Abre un Pull Request.

---

## Licencia & Créditos

Este proyecto está bajo **MIT License**. Consulta el archivo `LICENSE`.

**Créditos**:\
Alberto Velasco Fuentes\
Germán López Pérez
