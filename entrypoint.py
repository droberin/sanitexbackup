# -*- coding: utf-8 -*-
from sanitexbackup.create_backup import CreateBackup
from sanitexbackup.notifier import Notifier
from os import environ
from time import sleep

connection = {
    'host': 'remote_server',
    'user': 'root',
    'keyfile': '/home/user/.ssh/id_backups',
    'vm_name': 'virtual-machine'
}

#backup_creator = CreateBackup(connection)

#backup_result = backup_creator.create_backup()
#if backup_result is None:
#    print("failed")
#else:
#    print(backup_result)

botijo = Notifier(connection)
