CREATE TABLE IF NOT EXISTS words (
    id_words SERIAL PRIMARY KEY,
    english TEXT NOT NULL,
    russian TEXT NOT NULL,
    is_common BOOLEAN DEFAULT FALSE,
    UNIQUE(english, russian)
);

CREATE TABLE IF NOT EXISTS tg_users (
    id_users SERIAL PRIMARY KEY,
    tg_user_id BIGINT UNIQUE NOT NULL,
    user_name TEXT
);

CREATE TABLE IF NOT EXISTS user_words (
    id_u_words SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES tg_users(id_users),
    word_id INTEGER REFERENCES words(id_words),
    UNIQUE(user_id, word_id)
);

-- Базовые слова помечены как общие (is_common = TRUE)
INSERT INTO words (english, russian, is_common) VALUES
('house', 'дом', TRUE), ('window', 'окно', TRUE), ('he', 'он', TRUE),
('she', 'она', TRUE), ('red', 'красный', TRUE), ('blue', 'синий', TRUE),
('run', 'бежать', TRUE), ('sleep', 'спать', TRUE), ('bird', 'птица', TRUE),
('listen', 'слушать', TRUE), ('when', 'когда', TRUE), ('why', 'почему', TRUE),
('old', 'старый', TRUE), ('cold', 'холодный', TRUE), ('five', 'пять', TRUE),
('morning', 'утро', TRUE), ('today', 'сегодня', TRUE), ('kitchen', 'кухня', TRUE),
('milk', 'молоко', TRUE), ('train', 'поезд', TRUE), ('weather', 'погода', TRUE),
('boots', 'ботинки', TRUE), ('horse', 'лошадь', TRUE), ('jacket', 'куртка', TRUE),
('porridge', 'каша', TRUE), ('school', 'школа', TRUE), ('in', 'в', TRUE),
('for', 'для', TRUE), ('aunt', 'тётя', TRUE), ('brother', 'брат', TRUE),
('sand', 'песок', TRUE);