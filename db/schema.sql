START TRANSACTION;

CREATE TABLE IF NOT EXISTS Usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    moodle_id INT NOT NULL,
    telegram_id BIGINT UNIQUE,
    tipo TEXT NOT NULL,
    horario TEXT
) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

CREATE TABLE IF NOT EXISTS Grupos_tutoria (
    grupo_id INT AUTO_INCREMENT PRIMARY KEY,
    profesor_id INT NOT NULL,
    nombre_grupo VARCHAR(255) NOT NULL,
    tipo_grupo ENUM('privado', 'público') NOT NULL,
    asignatura_id INT NOT NULL,
    chat_id VARCHAR(100) UNIQUE,
    enlace_invitacion TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    en_uso BOOLEAN DEFAULT 0,
    FOREIGN KEY (profesor_id) REFERENCES Usuarios(id),
    UNIQUE INDEX(profesor_id, asignatura_id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

CREATE TABLE IF NOT EXISTS Valoraciones (
    valoracion_id INT AUTO_INCREMENT PRIMARY KEY,
    evaluador_id INT NOT NULL,
    profesor_id INT NOT NULL,
    puntuacion INT CHECK (puntuacion BETWEEN 1 AND 5),
    comentario TEXT,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    anonimo BOOLEAN DEFAULT 1,
    FOREIGN KEY (evaluador_id) REFERENCES Usuarios(id),
    FOREIGN KEY (profesor_id) REFERENCES Usuarios(id),
    UNIQUE INDEX(profesor_id, evaluador_id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

CREATE TABLE IF NOT EXISTS Mensajes (
    mensaje_id INT AUTO_INCREMENT PRIMARY KEY,
    telegram_id INT NOT NULL,
    chat_id VARCHAR(100) NOT NULL,
    sender_id INT,
    profesor_id INT NOT NULL,
    asignatura_id INT,
    texto TEXT,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profesor_id) REFERENCES Usuarios(id),
    FOREIGN KEY (sender_id) REFERENCES Usuarios(id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

CREATE TABLE IF NOT EXISTS Reacciones (
    reaccion_id INT AUTO_INCREMENT PRIMARY KEY,
    profesor_id INT NOT NULL,
    alumno_id INT NOT NULL,
    asignatura_id INT NOT NULL,
    emoji TEXT,
    cantidad INT,
    FOREIGN KEY (alumno_id) REFERENCES Usuarios(id),
    FOREIGN KEY (profesor_id) REFERENCES Usuarios(id),
    UNIQUE INDEX(profesor_id, alumno_id, asignatura_id, emoji)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

COMMIT;
