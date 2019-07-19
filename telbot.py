import telebot
import requests
import psycopg2
import urllib.parse as urlparse
import os
from datetime import datetime


url = urlparse.urlparse(os.environ['DATABASE_URL'])
dbname = url.path[1:]
user = url.username
password = url.password
host = url.hostname
port = url.port
bot = telebot.TeleBot('some API key')
keyboard1 = telebot.types.ReplyKeyboardMarkup(True)
keyboard1.row('Курс EUR/USD', 'Перевод ru->en')
keyboard1.row('Брать завтра зонт?', 'Выставки Москвы')


def EUR_USD():
    r = requests.get('https://www.cbr-xml-daily.ru/daily_json.js')
    data = r.json()
    USD = data['Valute']['USD']
    EUR = data['Valute']['EUR']

    if USD['Value'] > USD['Previous']:
        res = f"Доллар США $ {USD['Value']} ▲"
    else:
        res = f"Доллар США $ {USD['Value']} ▼"

    if EUR['Value'] > EUR['Previous']:
        res += f"\nЕвро € {EUR['Value']} ▲"
    else:
        res += f"\nЕвро € {EUR['Value']} ▼"
    return res


def translate(message):
    key = 'some API key'
    lang = 'ru-en'
    r = requests.get("https://translate.yandex.net/api/v1.5/tr.json/translate",
        params={'key': key, 'text': message.text, 'lang': lang})
    bot.send_message(message.chat.id, r.json()['text'][0])

def weather():
    appid = 'some API key'
    city = 'Moscow,ru'
    time_now = datetime.now()
    time_start = datetime(time_now.year, time_now.month, time_now.day + 1, 6, 0).strftime("%Y-%m-%d %H:%M:%S")
    time_stop = datetime(time_now.year, time_now.month, time_now.day + 1, 23, 0).strftime("%Y-%m-%d %H:%M:%S")
    r = requests.get(f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={appid}")
    weather = r.json()
    rain = False

    for i in weather['list']:
        if i['dt_txt'] > time_start and i['dt_txt'] < time_stop and i['weather'][0]['main'] == 'Rain':
            rain = True
            break   # break использован для повышения производительности бота

    if rain:
        str1 = "Ожидается дождь, возьмите с собой зонт!"
    else:
        str1 = "Дождя не ожидается, зонт вам не потребуется."
    return str1


def exhibition():
    res = ''
    api_key = 'some API key'
    r = requests.get('https://apidata.mos.ru/v1/datasets/527/features', params={'api_key': api_key})
    data = r.json()['features']
    for i in data:
        res += "*" + i['properties']['Attributes']['CommonName'] + "*\n"
        res += i['properties']['Attributes']['ObjectAddress'][0]['Address'] + "\n\n"
    return res


def add_new(message):
    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
    db = conn.cursor()
    db.execute(f"SELECT 1 FROM tele_users WHERE name='{message.text}'")
    res = db.fetchone()
    if res is None:
        db.execute(f"INSERT INTO tele_users (tele_id, name) VALUES\
            ({message.chat.id}, '{message.text}')")
        conn.commit()
        bot.send_message(message.chat.id, "Вы были успешно зарегистрированы!")
    else:
        bot.send_message(message.chat.id, "Это имя уже занято, повторите попытку /reg")
    db.close()
    conn.close()


@bot.message_handler(commands=['start'])
def start_message(message):
    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
    db = conn.cursor()
    db.execute("CREATE TABLE IF NOT EXISTS tele_users(user_id SERIAL PRIMARY KEY,\
    tele_id INT NOT NULL, name VARCHAR(50))")
    conn.commit()
    db.execute(f"SELECT name FROM tele_users WHERE tele_id={message.chat.id}")
    res = db.fetchone()
    if res is None:
        str1 = ' ты можешь зарегистрироваться написав /reg'
    else:
        str1 = ', ' + res[0]
    bot.send_message(message.chat.id, f"""\
Привет{str1}, я могу:
- сказать стоит ли брать завтра зонт;
- выдать курс EUR или USD к рублю;
- перевести текст с русского на английский;
- узнать о выставках проходящих в Москве.       
""", reply_markup=keyboard1)
    db.close()
    conn.close()

@bot.message_handler(commands=['reg'])
def registrate(message):
    conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
    db = conn.cursor()
    db.execute("CREATE TABLE IF NOT EXISTS tele_users(user_id SERIAL PRIMARY KEY,\
    tele_id INT NOT NULL, name VARCHAR(50))")
    conn.commit()
    db.execute(f"SELECT name FROM tele_users WHERE tele_id={message.chat.id}")
    res = db.fetchone()
    if res is None:
        msg = bot.send_message(message.chat.id, 'Введите ваше новое имя:')
        bot.register_next_step_handler(msg, add_new)
    else:
        bot.send_message(message.chat.id, res[0] + ' ты уже зарегистрирован!')
    db.close()
    conn.close()

@bot.message_handler(content_types=['text'])
def message_options(message):
    if message.text == 'Брать завтра зонт?':
        bot.send_message(message.chat.id, weather())
    elif message.text == 'Курс EUR/USD':
        bot.send_message(message.chat.id, EUR_USD())
    elif message.text == 'Перевод ru->en':
        msg = bot.send_message(message.chat.id, 'Введите слово/предложение для перевода:')
        bot.register_next_step_handler(msg, translate)
    elif message.text == 'Выставки Москвы':
        bot.send_message(message.chat.id, exhibition(), parse_mode= 'Markdown')
    else:
        bot.send_message(message.chat.id, 'Я вас не понимаю, для продолжения введите /start')

bot.polling(none_stop=True)