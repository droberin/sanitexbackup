# -*- coding: utf-8 -*-
from . import create_backup
import os
import sys
import time
import logging
import datetime
import pyotp
import json
import getopt

from telegram.ext import MessageHandler, Filters
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from time import gmtime, strftime

# logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


class Notifier:
    my_token = None
    updater = None
    dispatcher = None

    def __init__(self, connection=None):
        self.my_token = os.getenv('TELEGRAM_TOKEN', None)
        if self.my_token is None:
            logging.warning('No Telegram token found in environment var TELEGRAM_TOKEN')
            logging.info("Finishing Telegram bot process.")
            sys.exit(1)
        try:
            self.updater = Updater(token=self.my_token)
            self.dispatcher = self.updater.dispatcher
        except:
            logging.error("Token error")
            sys.exit(2)
        finally:
            logging.debug("End of token load process")

        if connection is not None:
            self.connection = connection
        else:
            self._define_connection()

        start_handler = CommandHandler('start', self.start)
        self.dispatcher.add_handler(start_handler)

        echo_handler = MessageHandler(Filters.text, self.echo)
        self.dispatcher.add_handler(echo_handler)

        self.updater.start_polling()
        self.updater.idle()

    def start(self, bot, update):
        bot.sendMessage(
            chat_id=update.message.chat_id,
            text="Hi, {}, here I am.\n"
                 "Tell me what you want!\n"
                 "\n"
                 "Perhaps a /help will be handy [TODO]\n"
                 "Userful commands:\n"
                 "\topen: to open a gate\n"
                 "\ttotp: provides a OTP code you can give to someone at the entrance\n"
                 "\ttoggle: toggles a gate\n"
                 "".format(update.message.chat.username)
        )
        logging.info("[START] ID {} requested a start (@{})".format(update.message.chat_id, update.message.chat.username))

    def _define_connection(self):
        _raise_error = False
        try:
            if self.connection is None:
                self.connection = {
                    'host': os.environ['SERVER'],
                    'keyfile': os.environ['KEYFILE'],
                    'user': os.environ.get('REMOTE_USER', 'root'),
                    'vm_name': os.environ['VM_NAME']
                }
        except KeyError as e:
            _raise_error = True
            message = "Connection not defined and env vars not found. ERROR: {}".format(e)
            logging.critical(message)
        finally:
            if _raise_error:
                return False

    def echo(self, bot, update):
        chat_id = str(update.message.chat_id)
        message = update.message.text
        incoming_photos = update.message.photo
        message_time = update.message.date
        current_time = datetime.datetime.fromtimestamp(time.time())
        diff_time = current_time - message_time
        full_name = str()
        try:
            if update.message.chat.first_name:
                full_name += update.message.chat.first_name
            if update.message.chat.last_name:
                if full_name == '':
                    full_name = update.message.chat.last_name
                else:
                    full_name += update.message.chat.last_name
        except TypeError:
            pass
        try:
            user_name = update.message.chat.username
        except KeyError:
            user_name = 'UnknownUserName'

        logging.debug("DEBUG: echo(): chat_id: {} [@{}] [Photos: {}]".format(chat_id, user_name, len(incoming_photos)))

        if diff_time.seconds > 10:
            logging.warning("[IGNORED] Old message ({}) has been received from {} [{}]"
                            "\n\tReachable through [ http://t.me/{} or tg://resolve?domain={} ]".format(
                                update.message.date,
                                chat_id,
                                full_name,
                                user_name,
                                user_name))
            return False
        if len(incoming_photos) > 0:
            logging.info("Some photos are coming!!! {}".format(len(incoming_photos)))

        if message.lower().startswith("configure"):
            if chat_id in valid_uids:
                params = message.split(' '),
                params = params[0]
                if len(params) > 1:
                    if params[1] == "phone":
                        if len(params) > 2:
                            logging.info("[{}] configured a new phone number.".format(chat_id))
                            current_phone_number = valid_uids[chat_id]['phone']
                            bot.sendMessage(chat_id=chat_id, text="Cambiado teléfono de '{}' a '{}'"
                                            .format(current_phone_number, params[2]))
                            valid_uids[chat_id]['phone'] = params[2]
                        else:
                            bot.sendMessage(chat_id=chat_id, text="Prueba a añadir también el número.")
                    elif params[1] == "name":
                        bot.sendMessage(chat_id=chat_id, text="No, no te dejo cambiarte el nombre. Te llamas {} y punto"
                                        .format(valid_uids[chat_id]['name']))
                    else:
                        bot.sendMessage(chat_id=chat_id, text="No sé qué hacer con eso. {}".format(params))
                else:
                    bot.sendMessage(chat_id=chat_id, text="Erm no idea {}".format(len(params)))
            else:
                bot.sendMessage(chat_id=chat_id, text="Que a ti ni agua.")

        elif message.lower().startswith("hi") or message.lower().startswith("hola"):
            if chat_id in valid_uids:
                bot.sendMessage(chat_id=chat_id, text="Hi, {}".format(user_name))
            else:
                bot.sendMessage(chat_id=chat_id, text="Hola, persona desconocida que se hace llamar «{}»".format(user_name))

        elif message.lower().startswith("push"):
            if chat_id in valid_uids:
                params = message.split(' '),
                params = params[0]
                if len(params) > 1:
                    device_name = params[1]
                    if len(params) > 2:
                        device_pin = int(params[2])
                    else:
                        device_pin = 18
                    result = request_push_to_device(device_name, 'gpio_push', device_pin)
                    logging.info("[{}] Requested Gate push: {} {}".format(user_name, device_name, device_pin))
                    bot.sendMessage(chat_id=chat_id, text="[PUSH] '{}' ({}): {}".format(device_name, device_pin, result))
                else:
                    bot.sendMessage(chat_id=chat_id, text="Device name required (pin number defaults 18).")
            else:
                bot.sendMessage(chat_id=chat_id, text="No, can't do\n"
                                                      "Tu ID es: {}".format(chat_id))
        elif message.lower().startswith("time"):
            showtime = strftime("%Y-%m-%d %H:%M:%S", gmtime())
            bot.sendMessage(chat_id=chat_id, text="GMT: {}".format(showtime))

        elif message.lower().startswith("totp"):
            if chat_id in valid_uids:
                if "totp_key" in valid_uids[chat_id]:
                    totp = pyotp.TOTP(valid_uids[chat_id]['totp_key'])
                    current_pass = totp.now()
                    bot.sendMessage(chat_id=chat_id, text="Current pass: {}".format(current_pass))
                else:
                    bot.sendMessage(chat_id=chat_id, text="Don't know your key... Sorry")
            else:
                logging.info("Unknown user: {}".format(chat_id))
                bot.sendMessage(chat_id=chat_id, text="Don't know you.")

        elif message.startswith("whoami"):
            bot.sendMessage(chat_id=chat_id, text="Eres: {}".format(chat_id))

        elif message.startswith("create backup"):
            if self.connection is None:
                bot.sendMessage(chat_id=chat_id, text="Connection not defined")
                return False
            new_backup = create_backup.CreateBackup(self.connection)
            data = new_backup.create_backup()
            del new_backup
            bot.sendMessage(chat_id=chat_id, text="Data: {}".format(data))

        elif message.startswith("list snapshots"):
            if self.connection is None:
                bot.sendMessage(chat_id=chat_id, text="Connection not defined")
                return False
            new_backup = create_backup.CreateBackup(self.connection)
            data = list(new_backup.list_snapshots())
            del new_backup
            _composed_message = "\n".join(data)
            bot.sendMessage(chat_id=chat_id, text="Snapshots of {}:\n{}".format(self.connection['vm_name'], _composed_message))

        elif message.startswith("create snapshot"):
            if self.connection is None:
                bot.sendMessage(chat_id=chat_id, text="Connection not defined")
                return False
            new_backup = create_backup.CreateBackup(self.connection)
            data = new_backup.create_snapshot()
            del new_backup
            _composed_message = "\n".join(data)
            bot.sendMessage(chat_id=chat_id, text="Data:\n{}".format(_composed_message))

        else:
            bot.sendMessage(chat_id=chat_id, text="No he entendido guay. Comienza nuevamente el proceso")
