START TRANSACTION;

CREATE TABLE IF NOT EXISTS Usuarios (
    Usuario_id INT AUTO_INCREMENT PRIMARY KEY,
    Nombre VARCHAR(255) NOT NULL,
    Apellidos VARCHAR(255),
    Tipo ENUM('estudiante', 'profesor'),
    Email_UGR VARCHAR(255) UNIQUE,
    TelegramID BIGINT UNIQUE,
    Horario TEXT
) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

CREATE TABLE IF NOT EXISTS Asignaturas (
    Asignatura_id INT AUTO_INCREMENT PRIMARY KEY,
    Nombre VARCHAR(255) UNIQUE NOT NULL
) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

CREATE TABLE IF NOT EXISTS Grupos_tutoria (
    Grupo_id INT AUTO_INCREMENT PRIMARY KEY,
    Profesor_id INT NOT NULL,
    Nombre_grupo VARCHAR(255) NOT NULL,
    Tipo_grupo ENUM('privada', 'pública') NOT NULL,
    Asignatura_id INT NOT NULL,
    Chat_id VARCHAR(100) UNIQUE,
    Enlace_invitacion TEXT,
    Fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    En_uso BOOLEAN DEFAULT 0,
    FOREIGN KEY (Asignatura_id) REFERENCES Asignaturas(Asignatura_id),
    FOREIGN KEY (Profesor_id) REFERENCES Usuarios(Usuario_id),
    UNIQUE INDEX(Profesor_id, Asignatura_id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

CREATE TABLE IF NOT EXISTS Matriculas (
    Matricula_id INT AUTO_INCREMENT PRIMARY KEY,
    Usuario_id INT NOT NULL,
    Asignatura_id INT NOT NULL,
    Tipo VARCHAR(20),
    FOREIGN KEY (Asignatura_id) REFERENCES Asignaturas(Asignatura_id),
    FOREIGN KEY (Usuario_id) REFERENCES Usuarios(Usuario_id),
    UNIQUE INDEX(Usuario_id, Asignatura_id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

CREATE TABLE IF NOT EXISTS Valoraciones (
    Valoracion_id INT AUTO_INCREMENT PRIMARY KEY,
    Evaluador_id INT NOT NULL,
    Profesor_id INT NOT NULL,
    Puntuacion INT CHECK (Puntuacion BETWEEN 1 AND 5),
    Comentario TEXT,
    Fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    Anonimo BOOLEAN DEFAULT 1,
    FOREIGN KEY (Evaluador_id) REFERENCES Usuarios(Usuario_id),
    FOREIGN KEY (Profesor_id) REFERENCES Usuarios(Usuario_id),
    UNIQUE INDEX(Profesor_id, Evaluador_id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

CREATE TABLE IF NOT EXISTS Mensajes (
    Mensaje_id INT AUTO_INCREMENT PRIMARY KEY,
    Telegram_id INT NOT NULL,
    Chat_id VARCHAR(100) NOT NULL,
    Sender_id INT NOT NULL,
    Profesor_id INT NOT NULL,
    Asignatura_id INT,
    Texto TEXT,
    Fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Asignatura_id) REFERENCES Asignaturas(Asignatura_id),
    FOREIGN KEY (Profesor_id) REFERENCES Usuarios(Usuario_id),
    FOREIGN KEY (Sender_id) REFERENCES Usuarios(Usuario_id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

CREATE TABLE IF NOT EXISTS Reacciones (
    Reaccion_id INT AUTO_INCREMENT PRIMARY KEY,
    Profesor_id INT NOT NULL,
    Alumno_id INT NOT NULL,
    Asignatura_id INT NOT NULL,
    Emoji TEXT,
    Cantidad INT,
    FOREIGN KEY (Alumno_id) REFERENCES Usuarios(Usuario_id),
    FOREIGN KEY (Profesor_id) REFERENCES Usuarios(Usuario_id),
    FOREIGN KEY (Asignatura_id) REFERENCES Asignaturas(Asignatura_id),
    UNIQUE INDEX(Profesor_id, Alumno_id, Asignatura_id, Emoji)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

COMMIT;
