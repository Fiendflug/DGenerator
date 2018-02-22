# -*- coding: utf-8 -*-

""" Подключение к удаленному серверу с помощью ssh туннеля. """

import paramiko
from sshtunnel import SSHTunnelForwarder
from os import path

class ServerConnect():
    def __init__(self,config):
        try:
            self.config = config
            self.address = self.config.get('SERVER', 'Address')
            self.username = self.config.get('SERVER', 'User')
            self.password = self.config.get('SERVER', 'Password')
            self.transport_port = self.config.get('SERVER', 'TransportPort')
            self.remote_port = self.config.get('SERVER', 'RemotePort')
            self.database_host = self.config.get('DATABASE', 'DatabaseHost')
            self.status_code = 'NO'
            self.tunnel = None
        except Exception as exc:
            print('ERROR: Ошибка конфигурации либо повреждены жизненно важные файлы приложения. '
                  'Дальнейшая работа невозможна Причина - %s. Проверьте журнал для получения информации.' % exc)

    def connect(self):
        try:
            if not self.status_code == 'YES':
                self.tunnel = SSHTunnelForwarder(
                    (self.address, int(self.transport_port)),
                    ssh_password=self.password,
                    ssh_username=self.username,
                    local_bind_address=(self.database_host, int(self.remote_port)),
                    remote_bind_address=(self.database_host, int(self.remote_port))
                )
                self.tunnel.start()
        except AssertionError as exc:
            print('ERROR: Ошибка создания ssh туннеля. Причина - %s' % exc.args)
        except Exception as exc:
            self.status_code = 'ERROR'
            print('ERROR: Ошибка создания ssh туннеля. Причина - %s' % exc.args)
        else:
            self.status_code = 'YES'

    def disconnect(self):
        try:
            if self.status_code == 'YES':
                self.tunnel.stop()
        except Exception as exc:
            self.status_code = 'ERROR'
            print(print('ERROR: Ошибка создания ssh туннеля.  Причина - %s' % exc.args))
        else:
            self.status_code = 'NO'

    def get_status(self):  # Получить текущий статус подключения
        return self.status_code

    def check_remote_cdr_path(self, active_sftp, path):  # Проверить существует ли удаленный каталог
        try:
            active_sftp.chdir(path)
        except IOError:
            return "BAD"
        else:
            return "OK"

    def cdr_transfer(self, local_dir, remote_dir):
        try:
            tunnel_was_active = False  # Был ли до вызова функции активен ssh туннель
            if self.get_status() == 'YES':
                self.disconnect()  # Отключаем ssh туннель
                tunnel_was_active = True

            ssh_transport = paramiko.Transport(self.address, int(self.transport_port))
            ssh_transport.connect(username=self.username, password=self.password)
            scp = paramiko.SFTPClient.from_transport(ssh_transport)

            if self.check_remote_cdr_path(scp, remote_dir) == 'BAD':
                scp.mkdir(remote_dir)  # ЕСли директория на сервере не существуе, создадим ее

            for index, cdr in enumerate(local_dir, start=1):
                cdr_name = path.basename(cdr)
                target_path = '%s/%s' % (remote_dir, cdr_name)
                scp.put(cdr, target_path)
                print('INFO: Файл %s из %s (%s) успешно передан на сервер.' %
                      (index, len(local_dir), cdr_name))
        except Exception as exc:
            print('ERROR: Ошибка передачи CDR файлов на сервер. Причина - %s. '
                  'Проверьте журнал для получения информации.'% exc)
        else:
            ssh_transport.close()
            if tunnel_was_active:
                self.connect()  # Подключаем ssh туннель вновь