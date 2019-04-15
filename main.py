import argparse
import os
import telebot
from datetime import datetime
from flask import Flask, request
from pymongo import MongoClient

API_TOKEN = os.environ['TOKEN']
bot = telebot.TeleBot(API_TOKEN)

server = Flask(__name__)
TELEBOT_URL = 'telebot_webhook/'
BASE_URL = 'https://example-telebot.herokuapp.com/'

MONGODB_URI = os.environ['MONGODB_URI']

mongo_client = MongoClient(MONGODB_URI)
mongo_db = mongo_client.get_default_database()
mongo_logs = mongo_db.get_collection('logs')


def reply_with_log(message, response):
    mongo_logs.insert_one({
        "text": message.text,
        "response": response,
        "user_nickname": message.from_user.username,
        "timestamp": datetime.utcnow()
    })
    bot.reply_to(message, response)


# Handle '/start' and '/help'
@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    reply_with_log(message, "Hi there, I am EchoBot. Just say anything nice and I'll say the exact same thing to you!")


# Handle all other messages with content_type 'text' (content_types defaults to ['text'])
@bot.message_handler(func=lambda message: True)
def echo_message(message):
    reply_with_log(message, message.text)


@server.route('/' + TELEBOT_URL + API_TOKEN, methods=['POST'])
def get_message():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=BASE_URL + TELEBOT_URL + API_TOKEN)
    return "!", 200


@server.route("/show_logs")
def show_logs():
    messages_list = list(mongo_logs.find())
    result = '<div>There are {} messages total. The last 10 are: </div><table>'.format(len(messages_list))
    row_template = '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'
    result += row_template.format('time', 'user', 'text from user', 'response from bot')
    for message in messages_list[-10:]:
        result += row_template.format(
            message['timestamp'], message['user_nickname'], message['text'], message['response']
        )
    result += '</table>'
    return result, 200


parser = argparse.ArgumentParser(description='Run the bot')
parser.add_argument('--poll', action='store_true')
args = parser.parse_args()

if args.poll:
    bot.remove_webhook()
    bot.polling()
else:
    # webhook should be set first
    webhook()
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
