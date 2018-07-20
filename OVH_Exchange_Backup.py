#!/usr/bin/python
# -*- coding: utf-8 -*-

from os import listdir, unlink, getpid
from os.path import isfile, isdir, join
from sys import exit
import requests
import time
import ovh


def main():
    client = ovh.Client(
        endpoint='ovh-eu',  # Endpoint of API OVH Europe
        application_key='',  # Application Key
        application_secret='',  # Application Secret
        consumer_key='',  # Consumer Key
    )

    ovh_organization = ''
    ovh_exchange_service = ''
    ovh_mail_acc = ''

    backup_filename = 'OVH_Exchange_' + time.strftime("%Y%m%d-%H%M%S") + '.pst'
    backup_dir = "/storage/backup/mail"
    backups_keep = 7

    pid_file = '/run/OVH_Exchange_Backup.pid'

    if isfile(pid_file):
        with open(pid_file, 'r') as old_pid:
            pid = old_pid.read()
            if isdir('/proc/' + pid) and pid != '':
                print('Script already running.')
                exit(1)
    open(pid_file, encoding='utf-8', mode='w').write(str(getpid()))

    api = Backups(client, ovh_organization, ovh_exchange_service, ovh_mail_acc)

    if api.check_backup_available():
        job_id = api.backup_delete()
        result = api.wait_for_task(job_id)
        if not result:
            print('OVH made a boo-boo and we don\'t know what did go wrong. Please try again.')
            exit(1)

    job_id = api.backup_create()
    result = api.wait_for_task(job_id)
    if not result:
        print('OVH made a boo-boo and we don\'t know what did go wrong. Please try again.')
        exit(1)

    job_id = api.dl_url_generate()
    result = api.wait_for_task(job_id)
    if not result:
        print('OVH made a boo-boo and we don\'t know what did go wrong. Please try again.')
        exit(1)

    dl_url = api.dl_url_get()

    api.dl_save_file(dl_url, backup_dir, backup_filename)

    api.rotate_backup_files(backup_dir, backups_keep)

    job_id = api.backup_delete()
    result = api.wait_for_task(job_id)
    if not result:
        print('OVH made a boo-boo and we don\'t know what did go wrong. Please try again.')
        exit(1)

    unlink(pid_file)


class Backups:
    def __init__(self, client, ovh_organization, ovh_exchange_service, ovh_mail_acc):
        self.ovh_organization = ovh_organization
        self.ovh_exchange_service = ovh_exchange_service
        self.ovh_mail_acc = ovh_mail_acc
        self.client = client

    def task_info(self, task_id):
        result = self.client.get('/email/exchange/{0}/service/{1}/account/{2}/tasks/{3}'.format(
            self.ovh_organization,
            self.ovh_exchange_service,
            self.ovh_mail_acc,
            task_id
        ))

        return result

    def wait_for_task(self, task_id):
        data = self.task_info(task_id)

        while data['status'] != 'error' and data['status'] != 'done':
            time.sleep(10)
            data = self.task_info(task_id)

        if data['status'] == 'error':
            return False
        else:
            return True

    def check_backup_available(self):
        try:
            self.client.get('/email/exchange/{0}/service/{1}/account/{2}/export'.format(
                self.ovh_organization,
                self.ovh_exchange_service,
                self.ovh_mail_acc
            ))
        except ovh.exceptions.ResourceNotFoundError:
            return False
        else:
            return True

    def backup_delete(self):
        result = self.client.delete('/email/exchange/{0}/service/{1}/account/{2}/export'.format(
            self.ovh_organization,
            self.ovh_exchange_service,
            self.ovh_mail_acc
        ))

        if 'id' in result:
            return result['id']
        else:
            return None

    def backup_create(self):
        result = self.client.post('/email/exchange/{0}/service/{1}/account/{2}/export'.format(
            self.ovh_organization,
            self.ovh_exchange_service,
            self.ovh_mail_acc
        ))

        if 'id' in result:
            return result['id']
        else:
            return None

    def dl_url_generate(self):
        result = self.client.post('/email/exchange/{0}/service/{1}/account/{2}/exportURL'.format(
            self.ovh_organization,
            self.ovh_exchange_service,
            self.ovh_mail_acc
        ))

        if 'id' in result:
            return result['id']
        else:
            return None

    def dl_url_get(self):
        result = self.client.get('/email/exchange/{0}/service/{1}/account/{2}/exportURL'.format(
            self.ovh_organization,
            self.ovh_exchange_service,
            self.ovh_mail_acc
        ))

        if 'url' in result:
            return result['url']
        else:
            return None

    def dl_save_file(self, url, backup_dir, backup_filename):
        data = requests.get(url, stream=True)

        with open(backup_dir + '/' + backup_filename, 'wb') as backup_file:
            for chunk in data.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    backup_file.write(chunk)

    def rotate_backup_files(self, backup_dir, backups_keep):
        backup_files = []
        for entry in listdir(backup_dir):
            if isfile(join(backup_dir, entry)):
                backup_files.append(join(backup_dir, entry))

        backup_files.sort(reverse=True)

        if len(backup_files) > backups_keep:
            for ct in range(backups_keep, len(backup_files)):
                unlink(backup_files[ct])


if __name__ == '__main__':
    main()
