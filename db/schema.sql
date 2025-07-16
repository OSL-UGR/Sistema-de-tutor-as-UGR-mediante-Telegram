START TRANSACTION;
-- Crear las tablas
CREATE TABLE IF NOT EXISTS Usuarios (
    Usuario_id INT AUTO_INCREMENT PRIMARY KEY,
    Nombre VARCHAR(255) NOT NULL,
    Apellidos VARCHAR(255),
    Tipo ENUM('estudiante', 'profesor'),
    Email_UGR VARCHAR(255) UNIQUE,
    TelegramID BIGINT UNIQUE,
    Horario TEXT
);

CREATE TABLE IF NOT EXISTS Asignaturas (
    Asignatura_id INT AUTO_INCREMENT PRIMARY KEY,
    Nombre VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS Grupos_tutoria (
    Grupo_id INT AUTO_INCREMENT PRIMARY KEY,
    Profesor_id INT NOT NULL,
    Nombre_grupo VARCHAR(255) NOT NULL,
    Tipo_grupo ENUM('privada', 'pública') NOT NULL,
    Asignatura_id INT,
    Chat_id VARCHAR(100) UNIQUE,
    Enlace_invitacion TEXT,
    Fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (Asignatura_id) REFERENCES Asignaturas(Asignatura_id),
    FOREIGN KEY (Profesor_id) REFERENCES Usuarios(Usuario_id)
);

CREATE TABLE IF NOT EXISTS Matriculas (
    Matricula_id INT AUTO_INCREMENT PRIMARY KEY,
    Usuario_id INT,
    Asignatura_id INT,
    Tipo VARCHAR(20),
    FOREIGN KEY (Asignatura_id) REFERENCES Asignaturas(Asignatura_id),
    FOREIGN KEY (Usuario_id) REFERENCES Usuarios(Usuario_id)
);

CREATE TABLE IF NOT EXISTS Valoraciones (
    Valoracion_id INT AUTO_INCREMENT PRIMARY KEY,
    Evaluador_id INT,
    Profesor_id INT,
    Puntuacion INT CHECK (Puntuacion BETWEEN 1 AND 5),
    Comentario TEXT,
    Fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    Anonimo BOOLEAN DEFAULT 1,
    FOREIGN KEY (Evaluador_id) REFERENCES Usuarios(Usuario_id),
    FOREIGN KEY (Profesor_id) REFERENCES Usuarios(Usuario_id)
);

COMMIT;
