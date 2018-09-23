# -*- coding: utf-8 -*-
# from sanitexbackup.create_backup import CreateBackup
from sanitexbackup.notifier import Notifier
from configloader import get_config_from_file
from os.path import expanduser, join as join_path, isdir
from os import mkdir, chmod
import logging

backups_path = '/app/backups'
if not isdir(backups_path):
    mkdir(backups_path, 0o700)
else:
    chmod(backups_path, 0o700)

connection = get_config_from_file()

if 'connection' in connection:
    connection = connection['connection']
# backup_creator = CreateBackup(connection)

if 'keyfile' not in connection:
    connection['keyfile'] = join_path(expanduser('~'), '.ssh', 'id_rsa')

if 'temporarily_remote_backup_path' not in connection:
    connection['temporarily_remote_backup_path'] = '/var/backups'

# backup_result = backup_creator.create_backup()
# if backup_result is None:
#     print("failed")
# else:
#     print(backup_result)

if 'host' in connection:
    logging.warning(
        'Remote backups will be created at {} in dir {}'.format(
            connection['host'],
            connection['temporarily_remote_backup_path']
        )
    )

my_robot = Notifier(connection)
