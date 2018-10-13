# -*- coding: utf-8 -*-
import logging
from os import path, mkdir, walk, sep
from paramiko import SSHClient, SSHException, AutoAddPolicy
from time import sleep
from xml.dom import minidom
import libvirt
from datetime import datetime


class CreateBackup:
    connection = dict()
    remote_path = None
    libvirt_connection = None
    snapshot_xml_template = """<domainsnapshot>
      <name>{}</name>
    </domainsnapshot>"""

    def __init__(self, connection):
        self.connection = connection
        if 'temporary_backup_path' in connection:
            self.remote_path = connection['temporarily_remote_backup_path']
        else:
            self.remote_path = '/var/backups'
        self.__connect_libvirt()

    def __connect_libvirt(self):
        try:
            self.libvirt_connection = libvirt.open(
                'qemu+ssh://{}@{}/system'.format(self.connection['user'], self.connection['host'])
            )
        except libvirt.libvirtError as e:
            logging.critical('Error connecting to Libvirt: {}'.format(e))
        if self.libvirt_connection is None:
            return False
        else:
            return True

    @staticmethod
    def _print_all_vm_disks(vm):
        raw_xml = vm.XMLDesc(0)
        xml = minidom.parseString(raw_xml)
        disk_types = xml.getElementsByTagName('disk')
        images_to_save = []
        for diskType in disk_types:
            print('disk: type=' + diskType.getAttribute('type') + ' device=' + diskType.getAttribute('device'))
            disk_nodes = diskType.childNodes
            for diskNode in disk_nodes:
                if diskNode.nodeName[0:1] != '#':
                    print('  ' + diskNode.nodeName)
                    for attr in diskNode.attributes.keys():
                        print('    ' + diskNode.attributes[attr].name + ' = ' +
                              diskNode.attributes[attr].value)
                        if diskType.getAttribute('device') == "disk" and diskNode.attributes[attr].name == "file" and \
                                diskNode.attributes[attr].value is not None:
                            images_to_save.append(diskNode.attributes[attr].value)
        return images_to_save

    def find_virtual_machine(self):
        if 'vm_name' not in self.connection:
            logging.critical('No virtual machine name was provided')
            return None
        else:
            try:
                if not self._is_libvirt_connected():
                    self.__connect_libvirt()
            except SSHException as e:
                logging.critical("SSH Error: {}".format(e))
                return None
            try:
                return self.libvirt_connection.lookupByName(self.connection['vm_name'])
            except libvirt.libvirtError as e:
                logging.warning('Error looking for VM "{}": {}'.format(self.connection['vm_name'], e))
                return None

    @staticmethod
    def _activate_vm(vm):
        if vm.isActive() != 1:
            resume_status = vm.create()
            if resume_status is None or resume_status is False:
                return False
        return True

    @staticmethod
    def _deactivate_vm(vm, sleep_time=5, retry_limit=10):
        if retry_limit < 2:
            return False
        if vm.isActive() == 1:
            deactivation_status = vm.shutdown()
            if deactivation_status:
                logging.warning(deactivation_status)
            sleep(sleep_time)
            for i in range(1, retry_limit):
                if vm.isActive() == 1:
                    logging.warning('VM is still active... [Try {}/{}] [{}s delay]'.format(i, retry_limit, sleep_time))
                    sleep(sleep_time)
                else:
                    break
            if vm.isActive() != 0:
                logging.critical('Machine did not stop in time... you may wanna increase delay or waiting time...')
                return False
        return True

    def _is_libvirt_connected(self):
        if self.libvirt_connection is None:
            return False
        return True

    def create_backup(self):
        current_backup_dir = None
        out = []
        if 'port' in self.connection:
            ssh_port = self.connection['port']
        else:
            ssh_port = 22
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        vm = self.find_virtual_machine()
        if vm is None:
            logging.critical('Failed to obtain VM')
            return False, current_backup_dir
        else:
            vm_status = vm.isActive()
            logging.warning('VM "{}" found [Status: {}]'.format(self.connection['vm_name'], vm_status))
            if vm.isActive() == 1:
                deactivation = self._deactivate_vm(vm)
                if not deactivation:
                    logging.critical('Could not shutdown machine.')
                    return False, current_backup_dir
            # return True

        images_to_save = self._print_all_vm_disks(vm)
        ssh.load_host_keys(filename=path.join(path.expanduser('~'), '.ssh', 'known_hosts'))
        try:
            ssh.connect(
                hostname=self.connection['host'],
                username=self.connection['user'],
                port=ssh_port,
                key_filename=self.connection['keyfile']
            )
        except SSHException as e:
            logging.critical('SSH Failed: {}'.format(e))
            ssh.close()
            return False, current_backup_dir
        try:
            current_backup_dir = datetime.today().strftime("backup-%Y%m%d%H%M")
            stdin, stdout, ssh_stderr = ssh.exec_command('mkdir {}/{}'.format(self.remote_path, current_backup_dir))
            stdin.flush()
            for image_to_save in images_to_save:
                stdin, stdout, ssh_stderr = ssh.exec_command(
                    'cp -v {} {}/{}'.format(image_to_save, self.remote_path, current_backup_dir)
                )
                out.append(stdout.readlines())
                stdin.flush()
            # Dump XML too
            ftp = ssh.open_sftp()
            ftp.chdir(self.remote_path + '/' + current_backup_dir)
            with ftp.open('VMdump.xml') as xml_dump_fp:
                xml_dump_fp.write(vm.XMLDesc())
            ftp.close()
        except SSHException as e:
            logging.critical('SSH error: {}'.format(e))
            return False, current_backup_dir
        if not self._activate_vm(vm):
            out.append("Failed to reactivate VM\n")
        return out, current_backup_dir

    @staticmethod
    def _print_scp_progress(filename, size, sent):
        logging.warning("%s\'s progress: %.2f%% \r" % (filename, float(sent) / float(size) * 100))

    def retrieve_backup(self, backup_name=None):
        if not backup_name:
            logging.warning('Tried to obtain a backup but no name was given')
            return False
        out = []
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
                key_filename=self.connection['keyfile']
            )
        except SSHException as e:
            logging.critical('SSH Failed: {}'.format(e))
            ssh.close()
            return False
        try:
            ftp = ssh.open_sftp()
            ftp.chdir(self.remote_path + '/' + backup_name)
            data = ftp.listdir()
            if not path.isdir('/app/backups/' + backup_name):
                mkdir('/app/backups/' + backup_name)
            for to_retrieve in data:
                logging.warning('Retrieving {} from backup {}'.format(to_retrieve, '/app/backups/' + backup_name))
                ftp.get(
                    to_retrieve,
                    '/app/backups/' + backup_name + '/' + to_retrieve)
        except SSHException as e:
            logging.critical('SSH error: {}'.format(e))
            return False
        except FileNotFoundError:
            out = 'Backup not found in remote server'
        return out

    def list_local_backups(self):
        return self._create_tree_from_path('/app/backups')

    @staticmethod
    def _create_tree_from_path(local_path):
        structure = str()
        for root, dirs, files in walk(local_path):
            level = root.replace(local_path, '').count(sep)
            indent = ' ' * 4 * (level)
            structure += ('{}{}/\n'.format(indent, path.basename(root)))
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                structure += ('{}{}\n'.format(subindent, f))
        return structure

    def list_remote_backups(self):
        out = []
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
                key_filename=self.connection['keyfile']
            )
        except SSHException as e:
            logging.critical('SSH Failed: {}'.format(e))
            ssh.close()
            return False
        try:
            stdin, stdout, ssh_stderr = ssh.exec_command(
                'cd {} && find . -type d -mindepth 1 -iname {}'.format('/var/backups', "backup-\*")
            )
            stdin.flush()
        except SSHException as e:
            logging.critical('SSH error: {}'.format(e))
            del ssh
            return False
        del ssh
        retrieved_data = stdout.readlines()
        return self._convert_backup_list_to_string(retrieved_data)

    @staticmethod
    def _convert_backup_list_to_string(retrieved_data):
        parsed_retrieved_data = str()
        for backup_unit_line in retrieved_data:
            if str(backup_unit_line).startswith('./'):
                parsed_retrieved_data += backup_unit_line[2:] + '\n'
            else:
                parsed_retrieved_data += backup_unit_line + '\n'
        return parsed_retrieved_data

    def list_snapshots(self):
        out = list()
        vm = self.find_virtual_machine()
        if vm is None:
            logging.critical('Failed to obtain VM')
            return False
        for snapshot in vm.listAllSnapshots():
            out.append(snapshot.getName())
        return out

    def create_snapshot(self, snapshot_name=None):
        out = list()
        vm = self.find_virtual_machine()
        if vm is None:
            logging.critical('Failed to obtain VM')
            return False
        else:
            if snapshot_name is None:
                snapshot_name = vm.name() + ' ' + datetime.today().strftime("%Y-%m-%d %H:%Mh")
            vm_status = vm.isActive()
            logging.info('VM "{}" found [Status: {}] trying to create {}'.format(
                self.connection['vm_name'],
                vm_status,
                snapshot_name)
            )
        try:
            snapshot_taken = vm.snapshotCreateXML(
                (self.snapshot_xml_template).format(snapshot_name),
                libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_ATOMIC
            )
            if snapshot_taken.getName() == snapshot_name:
                out = snapshot_name
        except libvirt.libvirtError as e:
            out = 'Snapshot error: {}'.format(e)
            logging.critical(out)
            return out
        return out
