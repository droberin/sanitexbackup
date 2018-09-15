# -*- coding: utf-8 -*-
import logging
from os import path
from paramiko import SSHClient, SSHException
from time import sleep
from xml.dom import minidom
import libvirt
from datetime import datetime


class CreateBackup:
    connection = dict()

    libvirt_connection = None
    snapshot_xml_template = """<domainsnapshot>
      <name>{}</name>
    </domainsnapshot>"""

    def __init__(self, connection, remote_path=None):
        self.connection = connection
        self.__connect_libvirt()
        if remote_path is None:
            self.remote_path = '/tmp/'

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

    def _print_all_vm_disks(self, vm):
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
                                diskNode.attributes[attr].value != None:
                            images_to_save.append(diskNode.attributes[attr].value)
        return images_to_save

    def find_virtual_machine(self):
        if 'vm_name' not in self.connection:
            logging.critical('No virtual machine name was provided')
            return None
        else:
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
        out = []
        if 'port' in self.connection:
            ssh_port = self.connection['port']
        else:
            ssh_port = 22
        ssh = SSHClient()
        vm = self.find_virtual_machine()
        if vm is None:
            logging.critical('Failed to obtain VM')
            return False
        else:
            vm_status = vm.isActive()
            logging.warning('VM "{}" found [Status: {}]'.format(self.connection['vm_name'], vm_status))
            if vm.isActive() == 1:
                deactivation = self._deactivate_vm(vm)
                if not deactivation:
                    logging.critical('Could not shutdown machine.')
                    return False
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
            return False
        try:
            for image_to_save in images_to_save:
                stdin, stdout, ssh_stderr = ssh.exec_command('cp -v {} {}'.format(image_to_save, self.remote_path),)
                out.append(stdout.readlines())
                stdin.flush()
        except SSHException as e:
            logging.critical('SSH error: {}'.format(e))
            return False
        if not self._activate_vm(vm):
            out.append("Failed to reactivate VM\n")
        return out

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
