# -*- coding: utf-8 -*-
from . import create_backup
import os
import sys
import time
import logging
import datetime
import pyotp

from telegram.ext import MessageHandler, Filters
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from time import gmtime, strftime

# logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


class Notifier:
    my_token = None
    updater = None
    dispatcher = None
    users = {}

    def __init__(self, connection=None,):
        if 'telegram_token' in connection:
            logging.warning("telegram token found in config!")
            self.my_token = connection['telegram_token']
        if self.my_token is None:
            logging.warning('No Telegram token found in environment var TELEGRAM_TOKEN')
            logging.info("Finishing Telegram bot process.")
            sys.exit(1)
        if 'users' in connection:
            if type(connection['users']) == dict:
                self.users = connection['users']
            else:
                logging.warning('User list configuration is not valid')
        try:
            self.updater = Updater(token=self.my_token)
            self.dispatcher = self.updater.dispatcher
        # This except is too damn hardcore...
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
        logging.warning("NotifierRobot running...")
        self.updater.idle()

    def start(self, bot, update):
        bot.sendMessage(
            chat_id=update.message.chat_id,
            text="Hi, {}, here I am.\n"
                 "Tell me what you want!\n"
                 "\n"
                 "Perhaps a /help will be handy [TODO]\n"
                 "Userful commands:\n"
                 "\tlist backups\n"
                 "\tcreate backup (MIND IT WILL STOP THE VM)\n"
                 "\tcreate snapshot\n"
                 "\tlist snapshots\n"
                 "\twhoami\n"
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
        chat_id = update.message.chat_id
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
            if chat_id in self.users:
                params = message.split(' '),
                params = params[0]
                if len(params) > 1:
                    if params[1] == "phone":
                        if len(params) > 2:
                            logging.info("[{}] configured a new phone number.".format(chat_id))
                            current_phone_number = self.users[chat_id]['phone']
                            bot.sendMessage(chat_id=chat_id, text="Cambiado teléfono de '{}' a '{}'"
                                            .format(current_phone_number, params[2]))
                            self.users[chat_id]['phone'] = params[2]
                        else:
                            bot.sendMessage(chat_id=chat_id, text="Prueba a añadir también el número.")
                    elif params[1] == "name":
                        bot.sendMessage(chat_id=chat_id, text="No, no te dejo cambiarte el nombre. Te llamas {} y punto"
                                        .format(self.users[chat_id]['name']))
                    else:
                        bot.sendMessage(chat_id=chat_id, text="No sé qué hacer con eso. {}".format(params))
                else:
                    bot.sendMessage(chat_id=chat_id, text="Erm no idea {}".format(len(params)))
            else:
                bot.sendMessage(chat_id=chat_id, text="Que a ti ni agua.")

        elif message.lower().startswith("hi") or message.lower().startswith("hola"):
            if chat_id in self.users:
                bot.sendMessage(chat_id=chat_id, text="Hi, {}".format(user_name))
            else:
                bot.sendMessage(
                    chat_id=chat_id,
                    text="Hola, persona desconocida que se hace llamar «{}»".format(user_name)
                )

        elif message.lower().startswith("time"):
            showtime = strftime("%Y-%m-%d %H:%M:%S", gmtime())
            bot.sendMessage(chat_id=chat_id, text="GMT: {}".format(showtime))

        elif message.lower().startswith("totp"):
            if chat_id in self.users:
                if "totp_key" in self.users[chat_id]:
                    totp = pyotp.TOTP(self.users[chat_id]['totp_key'])
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
            if chat_id in self.users:
                if self.connection is None:
                    bot.sendMessage(chat_id=chat_id, text="Connection not defined")
                    return False
                bot.sendMessage(chat_id=chat_id, text="Hold on, this may take a while...")
                new_backup = create_backup.CreateBackup(self.connection)
                (data, backup_name) = new_backup.create_backup()
                if backup_name:
                    logging.warning('New remote backup created: {}'.format(backup_name))
                    bot.sendMessage(chat_id=chat_id, text="Backup Name: {}".format(backup_name))
                else:
                    logging.warning('Failed to create new backup:\n{}'.format(data))
                del new_backup
                bot.sendMessage(chat_id=chat_id, text="Data: {}".format(data))
            else:
                logging.warning('Unknown user {} with ID {} tried to create a backup!'.format(user_name, chat_id))

        elif message.startswith("list backups"):
            if chat_id in self.users:
                if self.connection is None:
                    bot.sendMessage(chat_id=chat_id, text="Connection not defined")
                    return False
                new_backup = create_backup.CreateBackup(self.connection)
                data = list(new_backup.list_backups())
                del new_backup
                if data:
                    bot.sendMessage(
                        chat_id=chat_id,
                        text="backups of {}:\n{}".format(self.connection['vm_name'], data)
                    )
                else:
                    bot.sendMessage(
                        chat_id=chat_id,
                        text="Failed to list backups."
                    )
            else:
                logging.warning('Unknown user {} with ID {} tried to list backups!'.format(user_name, chat_id))

        elif message.startswith("retrieve backup") or message.startswith("get backup"):
            if chat_id in self.users:
                if self.connection is None:
                    bot.sendMessage(chat_id=chat_id, text="Connection not defined")
                    return False
                params = message.split(' '),
                params = params[0]
                if len(params) > 2:
                    if params[2] is None:
                        bot.sendMessage(chat_id=chat_id, text="Please, provide a backup name.")
                        return False
                backup_name = str(params[2])
                bot.sendMessage(chat_id=chat_id, text="Hold on, this may take a while... really...")
                new_backup = create_backup.CreateBackup(self.connection)
                data = new_backup.retrieve_backup(backup_name)
                del new_backup
                if data:
                    _composed_message = "\n".join(data)
                    bot.sendMessage(
                        chat_id=chat_id,
                        text="Result of backup {} retrieval:\n{}".format(backup_name, _composed_message)
                    )
                else:
                    bot.sendMessage(
                        chat_id=chat_id,
                        text="Failed to retrieve remote backup {}.".format(backup_name)
                    )
            else:
                logging.warning('Unknown user {} with ID {} tried to list backups!'.format(user_name, chat_id))

        elif message.startswith("list snapshots"):
            if chat_id in self.users:
                if self.connection is None:
                    bot.sendMessage(chat_id=chat_id, text="Connection not defined")
                    return False
                new_backup = create_backup.CreateBackup(self.connection)
                data = list(new_backup.list_snapshots())
                del new_backup
                _composed_message = "\n".join(data)
                bot.sendMessage(
                    chat_id=chat_id,
                    text="Snapshots of {}:\n{}".format(self.connection['vm_name'], _composed_message)
                )
            else:
                logging.warning('Unknown user {} with ID {} tried to list snapshots!'.format(user_name, chat_id))

        elif message.startswith("create snapshot"):
            if chat_id in self.users:
                if self.connection is None:
                    bot.sendMessage(chat_id=chat_id, text="Connection not defined")
                    return False
                new_backup = create_backup.CreateBackup(self.connection)
                data = new_backup.create_snapshot()
                del new_backup
                _composed_message = "\n".join(data)
                bot.sendMessage(chat_id=chat_id, text="Data:\n{}".format(_composed_message))
            else:
                logging.warning('Unknown user {} with ID {} tried to create a snapshot!'.format(user_name, chat_id))

        else:
            bot.sendMessage(chat_id=chat_id, text="Orden desconocida.")
