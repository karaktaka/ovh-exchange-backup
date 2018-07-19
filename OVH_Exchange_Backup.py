#!/usr/bin/python
# -*- coding: utf-8 -*-

from pprint import pprint
from hashlib import sha1
from os import listdir, unlink, getpid
from os.path import isfile, isdir, join
from sys import exit
import requests
import time
import json


def main():
    APP_KEY = ''
    APP_SEC = ''
    CONSUMER_KEY = ''

    OVH_ORGANIZATION = ''
    OVH_EXCHANGE_SERVICE = ''
    OVH_MAIL_ACC = ''
    OVH_API_URL = 'https://eu.api.ovh.com/1.0'

    BACKUP_FILENAME = 'OVH_Exchange_' + time.strftime("%Y%m%d-%H%M%S") + '.pst'
    BACKUP_DIR = "/storage/backup/mail"
    BACKUPS_KEEP = 7

    PID_FILE = '/tmp/OVH_Exchange_Backup.pid'

    ####################################################################################

    if isfile(PID_FILE):
        OLD_PID = file(PID_FILE, 'r').read()
        if isdir('/proc/' + OLD_PID) and OLD_PID != '':
            print 'Script already running.'
            exit(1)
    file(PID_FILE, 'w').write(str(getpid()))

    ####################################################################################

    OVH = Backups(APP_KEY, APP_SEC, CONSUMER_KEY, OVH_ORGANIZATION, OVH_EXCHANGE_SERVICE, OVH_MAIL_ACC, OVH_API_URL)

    if OVH.check_backup_available():
        JOB_ID = OVH.backup_delete()
        OVH.wait_for_task(unicode(JOB_ID))

    JOB_ID = OVH.backup_create()
    OVH.wait_for_task(unicode(JOB_ID))

    JOB_ID = OVH.dl_url_generate()
    OVH.wait_for_task(unicode(JOB_ID))

    DL_URL = OVH.dl_url_get()

    OVH.dl_save_file(DL_URL, BACKUP_DIR, BACKUP_FILENAME)

    OVH.rotate_backup_files(BACKUP_DIR, BACKUPS_KEEP)

    JOB_ID = OVH.backup_delete()
    OVH.wait_for_task(unicode(JOB_ID))

    ####################################################################################

    unlink(PID_FILE)


####################################################################################

class Backups:
    def __init__(self, APP_KEY, APP_SEC, CONSUMER_KEY, OVH_ORGANIZATION, OVH_EXCHANGE_SERVICE, OVH_MAIL_ACC,
                 OVH_API_URL):
        self.APP_KEY = APP_KEY
        self.APP_SEC = APP_SEC
        self.CONSUMER_KEY = CONSUMER_KEY
        self.OVH_ORGANIZATION = OVH_ORGANIZATION
        self.OVH_EXCHANGE_SERVICE = OVH_EXCHANGE_SERVICE
        self.OVH_MAIL_ACC = OVH_MAIL_ACC
        self.OVH_API_URL = OVH_API_URL
        self.HEADERS = {
            'X-Ovh-Application': self.APP_KEY,
            'X-Ovh-Consumer': self.CONSUMER_KEY,
            'X-Ovh-Timestamp': int(time.time()),
            'X-Ovh-Signature': '',
            'Content-type': 'application/json'
        }

        self.timeoffset = int(time.time()) - int(requests.get(self.OVH_API_URL + '/auth/time').text)

    ####################################################################################

    def do_request(self, METHOD, QUERY, BODY=''):
        self.HEADERS['X-Ovh-Timestamp'] = unicode(int(time.time()) + self.timeoffset)
        self.HEADERS['X-Ovh-Signature'] = '$1$' + sha1(
            self.APP_SEC + '+' + self.CONSUMER_KEY + '+' + METHOD + '+' + self.OVH_API_URL + QUERY + '+' + BODY + '+' +
            self.HEADERS['X-Ovh-Timestamp']).hexdigest()

        pprint('=== START ===')
        pprint(METHOD)
        pprint(self.HEADERS)
        pprint(QUERY)

        if METHOD.upper() == 'GET':
            DATA = requests.get(self.OVH_API_URL + QUERY, headers=self.HEADERS)
            DATA_SCODE = DATA.status_code
            DATA = json.loads(DATA.text)
        elif METHOD.upper() == 'POST':
            DATA = requests.post(self.OVH_API_URL + QUERY, headers=self.HEADERS)
            DATA_SCODE = DATA.status_code
            DATA = json.loads(DATA.text)
        elif METHOD.upper() == 'DELETE':
            DATA = requests.delete(self.OVH_API_URL + QUERY, headers=self.HEADERS)
            DATA_SCODE = DATA.status_code
            DATA = json.loads(DATA.text)
        else:
            DATA = False
            DATA_SCODE = False

        pprint('==> Result')
        pprint(DATA_SCODE)
        pprint(DATA)
        pprint('=== END ===')

        return DATA_SCODE, DATA

    ####################################################################################

    def task_info(self, TASK_ID):
        METHOD = 'GET'
        QUERY = '/email/exchange/' + self.OVH_ORGANIZATION + '/service/' + self.OVH_EXCHANGE_SERVICE + '/account/' + self.OVH_MAIL_ACC + '/tasks/' + TASK_ID

        (DATA_SCODE, DATA) = self.do_request(METHOD, QUERY)

        return DATA_SCODE, DATA

    ####################################################################################

    def wait_for_task(self, TASK_ID):
        (DATA_SCODE, DATA) = self.task_info(TASK_ID)

        while DATA['status'] != 'error' and DATA['status'] != 'done':
            time.sleep(60)
            (DATA_SCODE, DATA) = self.task_info(TASK_ID)

    ####################################################################################

    def check_backup_available(self):
        METHOD = 'GET'
        QUERY = '/email/exchange/' + self.OVH_ORGANIZATION + '/service/' + self.OVH_EXCHANGE_SERVICE + '/account/' + self.OVH_MAIL_ACC + '/export'

        (DATA_SCODE, DATA) = self.do_request(METHOD, QUERY)

        if DATA_SCODE == 200:
            AVAIL = True
        else:
            AVAIL = False

        return AVAIL

    ####################################################################################

    def backup_delete(self):
        METHOD = 'DELETE'
        QUERY = '/email/exchange/' + self.OVH_ORGANIZATION + '/service/' + self.OVH_EXCHANGE_SERVICE + '/account/' + self.OVH_MAIL_ACC + '/export'

        (DATA_SCODE, DATA) = self.do_request(METHOD, QUERY)

        if 'id' in DATA:
            return DATA['id']
        else:
            return None

    ####################################################################################

    def backup_create(self):
        METHOD = 'POST'
        QUERY = '/email/exchange/' + self.OVH_ORGANIZATION + '/service/' + self.OVH_EXCHANGE_SERVICE + '/account/' + self.OVH_MAIL_ACC + '/export'

        (DATA_SCODE, DATA) = self.do_request(METHOD, QUERY)

        if 'id' in DATA:
            return DATA['id']
        else:
            return None

    ####################################################################################

    def dl_url_generate(self):
        METHOD = 'POST'
        QUERY = '/email/exchange/' + self.OVH_ORGANIZATION + '/service/' + self.OVH_EXCHANGE_SERVICE + '/account/' + self.OVH_MAIL_ACC + '/exportURL'

        (DATA_SCODE, DATA) = self.do_request(METHOD, QUERY)

        if 'id' in DATA:
            return DATA['id']
        else:
            return None

    ####################################################################################

    def dl_url_get(self):
        METHOD = 'GET'
        QUERY = '/email/exchange/' + self.OVH_ORGANIZATION + '/service/' + self.OVH_EXCHANGE_SERVICE + '/account/' + self.OVH_MAIL_ACC + '/exportURL'

        (DATA_SCODE, DATA) = self.do_request(METHOD, QUERY)

        if 'url' in DATA:
            return DATA['url']
        else:
            return None

    ####################################################################################

    def dl_save_file(self, URL, BACKUP_DIR, BACKUP_FILENAME):
        DATA = requests.get(URL, stream=True)

        BACKUP_FILE = open(BACKUP_DIR + '/' + BACKUP_FILENAME, 'wb')
        for CHUNK in DATA.iter_content(chunk_size=1024 * 1024):
            if CHUNK:
                BACKUP_FILE.write(CHUNK)

        BACKUP_FILE.flush()
        BACKUP_FILE.close()

    ####################################################################################

    def rotate_backup_files(self, BACKUP_DIR, BACKUPS_KEEP):
        BACKUP_FILES = []
        for ENTRY in listdir(BACKUP_DIR):
            if isfile(join(BACKUP_DIR, ENTRY)):
                BACKUP_FILES.append(join(BACKUP_DIR, ENTRY))

        BACKUP_FILES.sort(reverse=True)

        if len(BACKUP_FILES) > BACKUPS_KEEP:
            for CT in range(BACKUPS_KEEP, len(BACKUP_FILES)):
                unlink(BACKUP_FILES[CT])


####################################################################################

if __name__ == '__main__':
    main()
