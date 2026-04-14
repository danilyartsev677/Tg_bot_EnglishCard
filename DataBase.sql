CREATE TABLE IF NOT EXISTS words (
    id_words SERIAL PRIMARY KEY,
    english TEXT NOT NULL,
    russian TEXT NOT null,
    UNIQUE(english, russian)
);

CREATE TABLE IF NOT EXISTS tg_users (
    id_users SERIAL PRIMARY KEY,
    tg_user_id  BIGINT UNIQUE NOT NULL,
    user_name TEXT
);

CREATE TABLE IF NOT EXISTS user_words (
    id_u_words SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES tg_users(id_users),
    word_id INTEGER REFERENCES words(id_words),
    UNIQUE(user_id, word_id)  
);

INSERT INTO words (english, russian) values
('house', 'дом'),
('window', 'окно'),
('he', 'он'),
('she', 'она'),
('red', 'красный'),
('blue', 'синий'),
('run', 'бежать'),
('sleep', 'спать'),
('bird', 'птица'),
('listen', 'слушать'),
('when', 'когда'),
('why', 'почему'),
('old', 'старый'),
('cold', 'холодный'),
('five', 'пять'),
('morning', 'утро'),
('today', 'сегодня'),
('kitchen', 'кухня'),
('milk', 'молоко'),
('train', 'поезд'),
('weather', 'погода'),
('boots', 'ботинки'),
('horse', 'лошадь'),
('jacket', 'куртка'),
('porridge', 'каша'),
('school', 'школа'),
('in', 'в'),
('for', 'для'),
('aunt', 'тётя'),
('brother', 'брат'),
('sand', 'песок');