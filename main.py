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
    cursor.execute(
        "INSERT INTO tg_users (tg_user_id, user_name) VALUES (%s, %s) ON CONFLICT (tg_user_id) DO NOTHING",
        (user_id, username)
    )
    connection.commit()
    cursor.close()
    connection.close()

def get_user_id(tg_user_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id_users FROM tg_users WHERE tg_user_id = %s", (tg_user_id,))
    result = cursor.fetchone()
    cursor.close()
    connection.close()
    return result[0] if result else None

def get_random_word_from_db(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    # Берем случайное слово из общей таблицы. Можно расширить до личных слов при необходимости.
    cursor.execute("SELECT english, russian FROM words ORDER BY RANDOM() LIMIT 1")
    result = cursor.fetchone()
    cursor.close()
    connection.close()
    if result:
        return {'english': result[0], 'russian': result[1]}
    return None

def get_other_words_from_db(target_word, count=3):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT english FROM words WHERE english != %s ORDER BY RANDOM() LIMIT %s",
        (target_word, count)
    )
    results = cursor.fetchall()  # fetchall возвращает список кортежей
    cursor.close()
    connection.close()
    return [row[0] for row in results]

def get_user_words_from_db(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        """SELECT w.english, w.russian
           FROM user_words uw
           JOIN words w ON uw.word_id = w.id_words
           WHERE uw.user_id = %s""",
        (user_id,)
    )
    results = cursor.fetchall()
    cursor.close()
    connection.close()
    return [{'english': row[0], 'russian': row[1]} for row in results]

def add_user_word_to_db(user_id, english, russian):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id_words FROM words WHERE english = %s AND russian = %s", (english, russian))
    word_id_result = cursor.fetchone()

    if word_id_result:
        word_id = word_id_result[0]
    else:
        cursor.execute("INSERT INTO words (english, russian) VALUES (%s, %s) RETURNING id_words", (english, russian))
        word_id = cursor.fetchone()[0]

    cursor.execute(
        "INSERT INTO user_words (user_id, word_id) VALUES (%s, %s) ON CONFLICT (user_id, word_id) DO NOTHING",
        (user_id, word_id)
    )
    connection.commit()
    cursor.close()
    connection.close()
    return True

def delete_user_word_from_db(user_id, english):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id_words FROM words WHERE english = %s", (english,))
    result = cursor.fetchone()
    if not result:
        cursor.close()
        connection.close()
        return False

    word_id = result[0]
    cursor.execute("DELETE FROM user_words WHERE word_id = %s", (word_id,))
    cursor.execute("DELETE FROM words WHERE id_words = %s", (word_id,))
    connection.commit()
    cursor.close()
    connection.close()
    return True

def get_next_word(user_id):
    word = get_random_word_from_db(user_id)
    if not word:
        return None, []
    other_words = get_other_words_from_db(word['english'])
    return word, other_words

@bot.message_handler(commands=['start'])
def start_command(message):
    register_user(message.from_user.id, message.from_user.username)
    welcome_text = (
        "Привет! Я - бот для изучения английских слов!\n"
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/cards - Начать изучение слов\n\n"
        "Что умеет этот бот:\n"
        "• Показывает русское слово и 4 варианта перевода на английский\n"
        "• Позволяет добавлять свои слова для изучения\n"
        "• Удаляет слова из вашего личного словаря\n\n"
        "Нажмите /cards, чтобы начать изучение!"
    )
    bot.send_message(message.chat.id, welcome_text)

@bot.message_handler(commands=['cards'])
def start_bot(message):
    register_user(message.from_user.id, message.from_user.username)
    user_id = get_user_id(message.from_user.id)
    if not user_id:
        bot.send_message(message.chat.id, "❌ Ошибка: пользователь не найден в базе.")
        return

    word_data, other_words = get_next_word(user_id)
    if not word_data:
        bot.send_message(message.chat.id, "📖 Словарь пуст. Добавьте слова через меню.")
        return

    markup = types.ReplyKeyboardMarkup(row_width=2)
    target_word = word_data['english']
    rus_word = word_data['russian']
    target_word_btn = types.KeyboardButton(target_word)
    other_words_btn = [types.KeyboardButton(word) for word in other_words]

    buttons = [target_word_btn] + other_words_btn
    random.shuffle(buttons)

    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    bot.send_message(
        message.chat.id,
        f'Выбери правильный перевод для слова: <b>{rus_word}</b>',
        parse_mode='HTML', reply_markup=markup
    )
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['rus_word'] = rus_word
        data['other_words'] = other_words
        data['user_id'] = user_id

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
        data['new_english'] = message.text.strip().lower()
    bot.send_message(message.chat.id, "Теперь напишите его перевод на русский:")
    bot.set_state(message.from_user.id, MyStates.add_russian, message.chat.id)

@bot.message_handler(state=MyStates.add_russian)
def add_russian_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        english_word = data['new_english']
    russian_word = message.text.strip().lower()
    user_id = get_user_id(message.from_user.id)
    if user_id and add_user_word_to_db(user_id, english_word, russian_word):
        bot.send_message(message.chat.id, f"✅ Слово '{english_word}' - '{russian_word}' успешно добавлено!")
    else:
        bot.send_message(message.chat.id, "❌ Не удалось добавить слово.")

    bot.delete_state(message.from_user.id, message.chat.id)
    start_bot(message)

@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word_command(message):
    user_id = get_user_id(message.from_user.id)
    if user_id:
        user_words = get_user_words_from_db(user_id)
        if user_words:
            markup = types.ReplyKeyboardMarkup(row_width=2)
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
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if 'target_word' in data:
            target_word = data['target_word']
            if message.text == target_word:
                bot.send_message(message.chat.id, '✅ Все правильно! Чтобы продолжить, нажмите кнопку "Дальше".')
            else:
                bot.send_message(message.chat.id, '❌ Неправильно! Попробуйте еще раз!')

if __name__ == '__main__':
    print('Бот запущен...')
    print('Для завершения нажмите Ctrl+C')
    bot.add_custom_filter(telebot.custom_filters.StateFilter(bot))
    bot.polling()