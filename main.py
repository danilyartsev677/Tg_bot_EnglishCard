import random
import config
import telebot
import psycopg2
from telebot import types
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

TOKEN = config.TOKEN
state_storage = StateMemoryStorage()
bot = telebot.TeleBot(TOKEN, state_storage=state_storage)

def get_db_connection():
    return psycopg2.connect(**config.DB_CONFIG)

class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'

class MyStates(StatesGroup):
    target_word = State()
    rus_word = State()
    other_words = State()
    add_english = State()
    add_russian = State()
    delete_word = State()

def register_user(user_id, username):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO tg_users (tg_user_id, user_name) VALUES (%s, %s) ON CONFLICT (tg_user_id) DO NOTHING",
            (user_id, username)
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()

def get_user_id(tg_user_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id_users FROM tg_users WHERE tg_user_id = %s", (tg_user_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        cursor.close()
        connection.close()

def get_quiz_words(user_id, count=4):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT w.english, w.russian
            FROM words w
            LEFT JOIN user_words uw ON w.id_words = uw.word_id
            WHERE uw.user_id IS NULL OR uw.user_id = %s
            ORDER BY RANDOM()
            LIMIT %s
        """, (user_id, count))
        results = cursor.fetchall()
        return [{'english': row[0], 'russian': row[1]} for row in results]
    finally:
        cursor.close()
        connection.close()

def get_user_words_from_db(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT w.english, w.russian
            FROM user_words uw
            JOIN words w ON uw.word_id = w.id_words
            WHERE uw.user_id = %s""",
            (user_id,)
        )
        results = cursor.fetchall()
        return [{'english': row[0], 'russian': row[1]} for row in results]
    finally:
        cursor.close()
        connection.close()

def add_user_word_to_db(user_id, english, russian):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        eng = english.strip().lower()
        rus = russian.strip().lower()

        cursor.execute("""
            SELECT 1 FROM user_words uw
            JOIN words w ON uw.word_id = w.id_words
            WHERE uw.user_id = %s AND LOWER(w.english) = %s AND LOWER(w.russian) = %s
        """, (user_id, eng, rus))

        if cursor.fetchone():
            return "already_added"

        cursor.execute("""
            SELECT id_words FROM words
            WHERE LOWER(english) = %s AND LOWER(russian) = %s
        """, (eng, rus))
        word_id_result = cursor.fetchone()

        if word_id_result:
            word_id = word_id_result[0]
            cursor.execute("""
                INSERT INTO user_words (user_id, word_id)
                SELECT %s, %s WHERE NOT EXISTS (
                    SELECT 1 FROM user_words WHERE user_id = %s AND word_id = %s
                )
            """, (user_id, word_id, user_id, word_id))
            connection.commit()
            return "common_word"
        else:
            cursor.execute(
                "INSERT INTO words (english, russian) VALUES (%s, %s) RETURNING id_words",
                (eng, rus)
            )
            word_id = cursor.fetchone()[0]

            cursor.execute(
                "INSERT INTO user_words (user_id, word_id) VALUES (%s, %s)",
                (user_id, word_id)
            )
            connection.commit()
            return "added_successfully"
    finally:
        cursor.close()
        connection.close()

def delete_user_word_from_db(user_id, english):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        eng_clean = english.strip().lower()
        cursor.execute("SELECT id_words FROM words WHERE LOWER(english) = %s", (eng_clean,))
        result = cursor.fetchone()
        if not result:
            return False

        word_id = result[0]
        cursor.execute("DELETE FROM user_words WHERE user_id = %s AND word_id = %s", (user_id, word_id))
        connection.commit()
        return True
    finally:
        cursor.close()
        connection.close()

@bot.message_handler(commands=['start'])
def start_command(message):
    register_user(message.from_user.id, message.from_user.username)
    welcome_text = (
        "Привет! Я - бот для изучения английских слов!\n "
        "Доступные команды:\n "
        "/start - Начать работу с ботом\n "
        "/cards - Начать изучение слов\n\n "
        "Что умеет этот бот:\n "
        "• Показывает русское слово и варианты перевода на английский\n "
        "• Позволяет добавлять свои слова для изучения\n "
        "• Удаляет слова из вашего личного словаря\n\n "
        "Нажмите /cards, чтобы начать изучение! "
    )
    bot.send_message(message.chat.id, welcome_text)

@bot.message_handler(commands=['cards'])
def start_bot(message):
    register_user(message.from_user.id, message.from_user.username)
    user_id = get_user_id(message.from_user.id)
    if not user_id:
        bot.send_message(message.chat.id, "❌ Ошибка: пользователь не найден в базе.")
        return

    words_list = get_quiz_words(user_id, count=4)
    if not words_list:
        bot.send_message(message.chat.id, "📖 Словарь пуст. Добавьте слова через меню.")
        return

    target = words_list[0]
    options = [w['english'] for w in words_list[1:]]

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [types.KeyboardButton(target['english'])] + [types.KeyboardButton(w) for w in options]
    random.shuffle(buttons)

    buttons.extend([
        types.KeyboardButton(Command.NEXT),
        types.KeyboardButton(Command.ADD_WORD),
        types.KeyboardButton(Command.DELETE_WORD)
    ])
    markup.add(*buttons)

    bot.send_message(
        message.chat.id,
        f'Выбери правильный перевод для слова: <b>{target["russian"]}</b>',
        parse_mode='HTML', reply_markup=markup
    )
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target['english']
        data['rus_word'] = target['russian']

@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_word(message):
    start_bot(message)

@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word_command(message):
    bot.send_message(message.chat.id, "Напишите слово на английском языке:")
    bot.set_state(message.from_user.id, MyStates.add_english, message.chat.id)

@bot.message_handler(state=MyStates.add_english)
def add_english_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['new_english'] = message.text.strip()
    bot.send_message(message.chat.id, "Теперь напишите его перевод на русский:")
    bot.set_state(message.from_user.id, MyStates.add_russian, message.chat.id)

@bot.message_handler(state=MyStates.add_russian)
def add_russian_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        english_word = data.get('new_english', '')
        russian_word = message.text.strip()
        user_id = get_user_id(message.from_user.id)

        if not user_id:
            bot.send_message(message.chat.id, "❌ Ошибка пользователя.")
            bot.delete_state(message.from_user.id, message.chat.id)
            return

        status = add_user_word_to_db(user_id, english_word, russian_word)

        if status == "already_added":
            bot.send_message(message.chat.id, f"ℹ️ Слово '{english_word}' - '{russian_word}' уже есть в вашем словаре.")
        elif status == "common_word":
            bot.send_message(message.chat.id, f"ℹ️ Такое слово уже есть в общем словаре. Я добавил его в ваш список.")
        else:
            bot.send_message(message.chat.id, f"✅ Слово '{english_word}' - '{russian_word}' успешно добавлено!")

        bot.delete_state(message.from_user.id, message.chat.id)
        start_bot(message)

@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word_command(message):
    user_id = get_user_id(message.from_user.id)
    if user_id:
        user_words = get_user_words_from_db(user_id)
        if user_words:
            markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            for word in user_words[:10]:
                markup.add(types.KeyboardButton(word['english']))
            markup.add(types.KeyboardButton("Отмена"))
            bot.send_message(message.chat.id, "Выберите слово для удаления:", reply_markup=markup)
            bot.set_state(message.from_user.id, MyStates.delete_word, message.chat.id)
        else:
            bot.send_message(message.chat.id, "У вас нет добавленных слов для удаления.")
    else:
        bot.send_message(message.chat.id, "Ошибка при получении данных пользователя.")

@bot.message_handler(state=MyStates.delete_word)
def delete_word_process(message):
    if message.text == "Отмена":
        bot.delete_state(message.from_user.id, message.chat.id)
        start_bot(message)
        return

    user_id = get_user_id(message.from_user.id)
    if user_id and delete_user_word_from_db(user_id, message.text):
        bot.send_message(message.chat.id, f"🗑 Слово '{message.text}' успешно удалено!")
    else:
        bot.send_message(message.chat.id, f"❌ Не удалось удалить слово '{message.text}' или оно не найдено.")

    bot.delete_state(message.from_user.id, message.chat.id)
    start_bot(message)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    if bot.get_state(message.from_user.id, message.chat.id) == MyStates.target_word:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            if 'target_word' in data:
                target_word = data['target_word']
                if message.text.strip().lower() == target_word.lower():
                    bot.send_message(message.chat.id, '✅ Все правильно! Чтобы продолжить, нажмите кнопку "Дальше".')
                else:
                    bot.send_message(message.chat.id, '❌ Неправильно! Попробуйте еще раз!')

if __name__ == '__main__':
    print('Бот запущен...')
    print('Для завершения нажмите Ctrl+C')
    bot.polling()