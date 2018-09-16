# -*- coding: utf-8 -*-
# from sanitexbackup.create_backup import CreateBackup
from sanitexbackup.notifier import Notifier
from configloader import get_config_from_file

connection = get_config_from_file()

if 'connection' in connection:
    connection = connection['connection']
# backup_creator = CreateBackup(connection)

if 'keyfile' not in connection:
    connection['keyfile'] = '/app/config/id_rsa'

# backup_result = backup_creator.create_backup()
# if backup_result is None:
#     print("failed")
# else:
#     print(backup_result)

my_robot = Notifier(connection)
