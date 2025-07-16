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
4. Configura variables de entorno copiando `datos.env.example` a `datos.env` y completando los valores.
5. Inicializa la base de datos (se auto-crea al iniciar el bot si no existe).

---

## Uso

### Iniciar bot de registro

```bash
python main.py
```

Envía `/start` en Telegram para comenzar el alta.

### Iniciar bot de grupos

```bash
python bot_grupo_main.py
```

Agregar el bot como admin en un grupo para habilitar la configuración.

**Comandos principales**:

* `/start`
* `/tutoria`
* `/configurar_horario`
* `/crear_grupo_tutoria`
* `/ver_misdatos`

---

## Estructura del Repositorio

```
├── main.py
├── bot_grupo_main.py
├── handlers/       # Lógica de negocio
├── db/             # Consultas SQL
├── utils/          # Módulos auxiliares
├── data/           # Excel y DB inicial
├── docs/           # Imágenes y diagramas
└── datos.env.txt.example
```

---

## Resumen del TFG

**Título**: Diseño, desarrollo y despliegue de una arquitectura en tres capas para la gestión de citas, grupos y horarios

**Autor**: Alberto Velasco Fuentes

**Director**: Gabriel Maciá Fernández

**Contexto**: La gestión tradicional de tutorías mediante correo electrónico genera demoras y confusiones; el proyecto propone mejorar la experiencia mediante bots de Telegram.

**Objetivos**:

* Automatizar el alta de usuarios.
* Facilitar la reserva y gestión de tutorías.
* Proporcionar métricas de uso.

**Metodología**: Desarrollo en Python con la librería `python-telegram-bot`, diseño en tres capas y pruebas funcionales.

**Resultados**: Reducción del tiempo de reserva a segundos, mejora en la puntualidad y sistema escalable.

**Conclusiones**: El prototipo demuestra viabilidad y beneficios claros; se recomienda integración de videoconferencia y mejoras UX.

---

## Roadmap / Futuras mejoras

* Integración de videollamadas.
* Frontend web de administración.
* Sistema de notificaciones via email.

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

**Créditos**:
Alberto Velasco Fuentes
