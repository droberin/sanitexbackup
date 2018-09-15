# -*- coding: utf-8 -*-
import logging
from sanitexbackup.retrieve_backup import RetrieveBackup
from sanitexbackup.create_backup import CreateBackup
from os import environ, path


if __name__ == '__main__':
    if 'SERVER' not in environ or "VM_NAME" not in environ:
        logging.critical('Server must be defined in env var SERVER and Virtual Machine name in VM_NAME.')
        exit(1)
    if 'USER' in environ:
        user = environ['USER']
    else:
        user = 'root'
    my_connection = {
        'host': environ['SERVER'],
        'user': user,
        'keyfile': path.expanduser('~') + '/.ssh/id_backup',
        'vm_name': environ['VM_NAME']
    }

    if 'local_path' in environ:
        my_local_path = environ['local_path']
    else:
        my_local_path = '/media/backups'

    if not my_local_path.endswith('/'):
        my_local_path += '/'

    backup_maker = CreateBackup(my_connection)
    data = backup_maker.create_backup()
    if data:
        logging.warning(data)
    else:
        logging.critical("Could not create remote backup")
        exit(1)
    exit(0)
    backup_getter = RetrieveBackup(my_connection, my_local_path)
    if not backup_getter.check_if_local_path_exists():
        if not backup_getter.create_local_path():
            logging.critical("Could not create local directory {}".format(backup_getter.get_local_path))
            exit(1)
    if not backup_getter.get():
        logging.critical('Failed to obtain backup')
        exit(1)
else:
    print("This file shouldn't be loaded as a module...")
