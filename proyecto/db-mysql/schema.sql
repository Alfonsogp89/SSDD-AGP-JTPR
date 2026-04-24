CREATE SCHEMA IF NOT EXISTS ssdd;
USE ssdd;

CREATE TABLE IF NOT EXISTS users(
	id varchar(50),
       	email varchar(50),
	password_hash text,
       	name text,
	token text,
	visits int,
	PRIMARY KEY(id)
);

-- Para búsquedas con email
CREATE INDEX user_email_idx ON users (email);

-- Tabla de diálogos/conversaciones
CREATE TABLE IF NOT EXISTS dialogues(
	id INT AUTO_INCREMENT PRIMARY KEY,
	user_id VARCHAR(50) NOT NULL,
	name VARCHAR(100) NOT NULL,
	status ENUM('READY', 'BUSY', 'FINISHED') DEFAULT 'READY',
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	FOREIGN KEY (user_id) REFERENCES users(id),
	UNIQUE KEY unique_user_dialogue (user_id, name)
);

-- Tabla de mensajes dentro de diálogos
CREATE TABLE IF NOT EXISTS messages(
	id INT AUTO_INCREMENT PRIMARY KEY,
	dialogue_id INT NOT NULL,
	role ENUM('user', 'assistant') NOT NULL,
	content LONGTEXT NOT NULL,
	timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (dialogue_id) REFERENCES dialogues(id) ON DELETE CASCADE
);

-- CUIDADO!! AÑADO UN USUARIO PARA PROBAR, PASSWORD: "admin"
INSERT INTO users VALUES ("dsevilla", "dsevilla@um.es", "21232f297a57a5a743894a0e4a801fc3", "diego", "TOKEN", 0);

