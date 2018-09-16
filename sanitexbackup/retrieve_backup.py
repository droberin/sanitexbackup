# -*- coding: utf-8 -*-
import logging
from os import path, mkdir
from scp import SCPClient, SCPException
from paramiko import SSHClient, SSHException, AutoAddPolicy


class RetrieveBackup:
    local_path = None
    remote_path = None
    connection = dict()

    def __init__(self, connection, local_path, remote_path=None):
        self.connection = connection
        self.local_path = local_path
        self.remote_path = remote_path

    def check_if_local_path_exists(self):
        return path.isdir(self.local_path)

    def get_local_path(self):
        return self.local_path

    def create_local_path(self):
        try:
            mkdir(self.local_path, 0o700)
        except PermissionError:
            logging.critical('Local Path {} does not exist nor can be created')
            return False
        except FileExistsError:
            logging.warning('Local path {} already exists'.format(self.local_path))
            return False
        return True

    def get(self):
        if not self.remote_path:
            logging.critical('Remote file not specified')
            return False
        try:
            if 'host' not in self.connection or 'user' not in self.connection or 'keyfile' not in self.connection:
                logging.critical('No correct connection definition data set')
                return False
        except KeyError as e:
            logging.critical('Error while reading key: {}'.format(e))
        if 'port' in self.connection:
            ssh_port = self.connection['port']
        else:
            ssh_port = 22
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.load_host_keys(filename=path.join(path.expanduser('~'), '.ssh', 'known_hosts'))
        try:
            ssh.connect(
                hostname=self.connection['host'],
                username=self.connection['user'],
                port=ssh_port,
                key_filename=self.connection['keyfile'],
            )
        except SSHException as e:
            logging.critical('SSH Failed: {}'.format(e))
            ssh.close()
            return False
        try:
            with SCPClient(ssh.get_transport()) as scp:
                scp.get(self.remote_path, self.local_path)
            return True
        except SCPException as e:
            logging.critical("Failed to retrieve backup: {}".format(e))
            ssh.close()
            return False
