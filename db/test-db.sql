START TRANSACTION;

DROP TABLE IF EXISTS Valoraciones;
DROP TABLE IF EXISTS Reacciones;
DROP TABLE IF EXISTS Mensajes;
DROP TABLE IF EXISTS Matriculas;
DROP TABLE IF EXISTS Grupos_tutoria;
DROP TABLE IF EXISTS Asignaturas;
DROP TABLE IF EXISTS Usuarios;

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


-- Inserciones en Usuarios
INSERT INTO Usuarios VALUES (1, 'Alberto', 'Velasco Fuentes', 'profesor', 'alb172@correo.ugr.es', 7179702007, 'Lunes 09:00-11:00, Lunes 11:00-13:00, Martes 12:30-14:00, Miércoles 09:00-14:00, Jueves 09:00-14:00');
INSERT INTO Usuarios VALUES (2, 'Lucía', 'Martín López', 'estudiante', 'jmcastillogarcia@ugr.es', 15182393, NULL);
INSERT INTO Usuarios VALUES (3, 'Javier', 'Gómez Ruiz', 'profesor', 'dirosl@ugr.es', NULL, NULL);
INSERT INTO Usuarios VALUES (4, 'Marta', 'Pérez García', 'profesor', 'dirceprud@ugr.es', NULL, NULL);
INSERT INTO Usuarios VALUES (5, 'Carlos', 'Rodríguez Díaz', 'estudiante', 'gmacia@ugr.es', NULL, NULL);
INSERT INTO Usuarios VALUES (6, 'Ana', 'Fernández Cano', 'profesor', 'vicedigital@ugr.es', NULL, NULL);
INSERT INTO Usuarios VALUES (7, 'Elena', 'Morales Díaz', 'estudiante', 'aguillen@ugr.es', NULL, NULL);
INSERT INTO Usuarios VALUES (8, 'Ricardo', 'López Herrera', 'estudiante', 'pablogarcia@ugr.es', NULL, NULL);
INSERT INTO Usuarios VALUES (9, 'Sonia', 'Martínez Robles', 'estudiante', NULL, NULL, NULL);
INSERT INTO Usuarios VALUES (10, 'Miguel', 'Torres Gutiérrez', 'estudiante', NULL, NULL, NULL);
INSERT INTO Usuarios VALUES (11, 'Laura', 'Ruiz Fernández', 'estudiante', NULL, NULL, NULL);
INSERT INTO Usuarios VALUES (12, 'Gabriel', 'Maciá Fernandez', 'estudiante', NULL, NULL, NULL);
INSERT INTO Usuarios VALUES (13, 'Jose ramon', 'Velasco Fuentes', 'estudiante', 'joseravelgar@gmail.com', 79419879910, NULL);
INSERT INTO Usuarios VALUES (14, 'Germán', 'López Pérez', 'estudiante', 'gerlope@correo.ugr.es', 7112555193, NULL);

-- Inserciones en Asignaturas
INSERT INTO Asignaturas VALUES (1, 'Tutoria');
INSERT INTO Asignaturas VALUES (2, 'ST');
INSERT INTO Asignaturas VALUES (3, 'SRC');
INSERT INTO Asignaturas VALUES (4, 'RIM');
INSERT INTO Asignaturas VALUES (5, 'IES');
INSERT INTO Asignaturas VALUES (6, 'LMD');
INSERT INTO Asignaturas VALUES (7, 'TOC');
INSERT INTO Asignaturas VALUES (8, 'FIS');
INSERT INTO Asignaturas VALUES (9, 'IA');
INSERT INTO Asignaturas VALUES (10, 'ISI');
INSERT INTO Asignaturas VALUES (11, 'ABD');
INSERT INTO Asignaturas VALUES (12, 'SWAP');
INSERT INTO Asignaturas VALUES (13, 'ACAP');

-- Inserciones en Grupos_tutoria
INSERT INTO Grupos_tutoria VALUES (20, 1, 'Tutoría Privada - Prof. Alberto', 'privada', 1, '-4871774149', 'https://t.me/+fuljSS2qK1FjYzY8', '2025-07-07 07:54:53', 0);
INSERT INTO Grupos_tutoria VALUES (24, 1, 'ST - Avisos', 'pública', 2, '-1002817992062', 'https://t.me/+DckKNiC7qNszMzQ8', '2025-07-11 07:11:50', 0);
INSERT INTO Grupos_tutoria VALUES (25, 1, 'SRC - Avisos', 'pública', 3, '-4915176092', 'https://t.me/+AKxgOASQArRmNDc0', '2025-07-11 07:19:21', 0);
INSERT INTO Grupos_tutoria VALUES (27, 1, 'RIM - Avisos', 'pública', 4, '-4855478353', 'https://t.me/+YSAgX-ORFpE5N2I0', '2025-07-11 07:22:19', 0);

-- Inserciones en Matriculas
INSERT INTO Matriculas VALUES (1, 1, 2, 'docente');
INSERT INTO Matriculas VALUES (2, 1, 3, 'docente');
INSERT INTO Matriculas VALUES (3, 1, 4, 'docente');
INSERT INTO Matriculas VALUES (4, 2, 2, 'estudiante');
INSERT INTO Matriculas VALUES (5, 2, 3, 'estudiante');
INSERT INTO Matriculas VALUES (6, 2, 4, 'estudiante');
INSERT INTO Matriculas VALUES (7, 3, 5, 'docente');
INSERT INTO Matriculas VALUES (8, 3, 6, 'docente');
INSERT INTO Matriculas VALUES (9, 3, 3, 'docente');
INSERT INTO Matriculas VALUES (10, 4, 8, 'docente');
INSERT INTO Matriculas VALUES (11, 4, 9, 'docente');
INSERT INTO Matriculas VALUES (12, 4, 2, 'docente');
INSERT INTO Matriculas VALUES (13, 5, 11, 'estudiante');
INSERT INTO Matriculas VALUES (14, 5, 12, 'estudiante');
INSERT INTO Matriculas VALUES (15, 5, 13, 'estudiante');
INSERT INTO Matriculas VALUES (16, 6, 11, 'docente');
INSERT INTO Matriculas VALUES (17, 6, 12, 'docente');
INSERT INTO Matriculas VALUES (18, 6, 4, 'docente');
INSERT INTO Matriculas VALUES (19, 7, 8, 'estudiante');
INSERT INTO Matriculas VALUES (20, 7, 9, 'estudiante');
INSERT INTO Matriculas VALUES (21, 7, 10, 'estudiante');
INSERT INTO Matriculas VALUES (22, 8, 5, 'estudiante');
INSERT INTO Matriculas VALUES (23, 8, 6, 'estudiante');
INSERT INTO Matriculas VALUES (24, 8, 7, 'estudiante');
INSERT INTO Matriculas VALUES (25, 12, 3, 'estudiante');
INSERT INTO Matriculas VALUES (26, 12, 4, 'estudiante');
INSERT INTO Matriculas VALUES (27, 13, 2, 'estudiante');
INSERT INTO Matriculas VALUES (28, 13, 3, 'estudiante');
INSERT INTO Matriculas VALUES (29, 13, 4, 'estudiante');
INSERT INTO Matriculas VALUES (30, 14, 2, 'estudiante');
INSERT INTO Matriculas VALUES (31, 14, 3, 'estudiante');
INSERT INTO Matriculas VALUES (32, 14, 4, 'estudiante');

-- Inserciones en Valoraciones
INSERT INTO Valoraciones VALUES (1, 2, 1, 4, 'test', NULL, 0);
INSERT INTO Valoraciones VALUES (25, 14, 1, 1, 'dawfew3gsgrhgdrhthgrtdghr', '2025-07-09 10:29:30', 0);

COMMIT;