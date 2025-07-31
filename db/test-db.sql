START TRANSACTION;

DROP TABLE IF EXISTS Valoraciones;
DROP TABLE IF EXISTS Reacciones;
DROP TABLE IF EXISTS Mensajes;
DROP TABLE IF EXISTS Grupos_tutoria;
DROP TABLE IF EXISTS Usuarios;

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


-- Inserciones en Usuarios
INSERT INTO Usuarios VALUES (1, 4, 7179702007, 'editingteacher', 'Lunes 09:00-11:00, Lunes 11:00-13:00, Martes 12:30-14:00, Miércoles 09:00-14:00, Jueves 09:00-14:00');
INSERT INTO Usuarios VALUES (2, 5, NULL, 'editingteacher', NULL);
INSERT INTO Usuarios VALUES (3, 3, 7112555193, 'student', NULL);

-- Inserciones en Grupos_tutoria
INSERT INTO Grupos_tutoria VALUES (20, 1, 'Tutoría Privada - Prof. Alberto', 'privado', 1, '-4871774149', 'https://t.me/+fuljSS2qK1FjYzY8', '2025-07-07 07:54:53', 0);
INSERT INTO Grupos_tutoria VALUES (24, 1, 'ST - Avisos', 'público', 2, '-1002817992062', 'https://t.me/+DckKNiC7qNszMzQ8', '2025-07-11 07:11:50', 0);
INSERT INTO Grupos_tutoria VALUES (25, 1, 'SRC - Avisos', 'público', 3, '-4915176092', 'https://t.me/+AKxgOASQArRmNDc0', '2025-07-11 07:19:21', 0);
INSERT INTO Grupos_tutoria VALUES (27, 1, 'RIM - Avisos', 'público', 4, '-4855478353', 'https://t.me/+YSAgX-ORFpE5N2I0', '2025-07-11 07:22:19', 0);

-- Inserciones en Valoraciones
INSERT INTO Valoraciones VALUES (1, 2, 1, 4, 'test', NULL, 0);
INSERT INTO Valoraciones VALUES (25, 3, 1, 1, 'dawfew3gsgrhgdrhthgrtdghr', '2025-07-09 10:29:30', 0);

COMMIT;