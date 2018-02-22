# -*- coding: utf-8 -*-

""" Модуль для конвертирования CDR записей, трансфера их на сервер UTM5 и запуска утилиты utm5_send_cdr для обсчета
 переданных и сконвертированных CDR файлов"""

import utm_connect
import custom_exceptions
import subprocess
from os import path, listdir, makedirs

class Cdr:
    def __init__(self, period, config):
        try:
            self.status = {
                'convert': 'READY',
                'transfer': 'READY',
                'parse': 'READY'
            }
            self.config = config
            self.period = '%s_%s' % tuple(period)
            self.cdr_upload_dir = path.join(path.normpath(self.config.get('CDR', 'SourceRootCdrDir')), self.period)
            self.cdr_converted_dir = path.join(path.normpath(self.config.get('CDR', 'ConvertedRootCdrDir')),
                                               self.period)
            self.remote_cdr_dir = path.join(self.config.get('CDR', 'RemotePath'), self.period)
            self.parser = self.config.get('CDR', 'ParserPath')
            self.parser_config = self.config.get('CDR', 'ParserConfigPath')
        except Exception as exc:
            print('ERROR: Ошибка конфигурации либо повреждены жизненно важные файлы приложения. '
                  'Дальнейшая работа невозможна Причина - %s. Проверьте журнал для получения информации.' % exc)

    def convert(self): # Преобразовать CDR в формат UTM5
        try:
            if path.isdir(self.cdr_upload_dir) and len(listdir(self.cdr_upload_dir)) != 0:
                if not path.isdir(self.cdr_converted_dir):
                    makedirs(self.cdr_converted_dir)
                # cdr_count = 1
                for index, cdr in enumerate(listdir(self.cdr_upload_dir), start=1):
                    converted_cdr_name = cdr.replace('.log', '.cdr')
                    converted_cdr_lines = []
                    line_count = 0
                    for line in open(path.join(self.cdr_upload_dir, cdr)):
                        temp = line.split()
                        converted_cdr_lines.append(
                            '%s;%s;%s;%s;%s %s;%s;%s;1\n' %
                            (temp[1], temp[3], temp[6], str(line_count), temp[4], temp[5], temp[0][1:], temp[2]))
                        line_count += 1
                    converted_cdr_file = open(path.join(self.cdr_converted_dir, converted_cdr_name), 'w+')
                    converted_cdr_file.writelines(converted_cdr_lines)
                    print('INFO: Файл %s из %s (%s) успешно сконвертирован' %
                                     (index, len(listdir(self.cdr_upload_dir)), cdr))
                    # cdr_count += 1
            else:
                raise custom_exceptions.NoUploadDirException
        except custom_exceptions.NoUploadDirException:
            print('ERROR: Не обнаружен каталог с CDR файлами либо файлы в каталоге, которые необходимо обработать')
            self.status['convert'] = 'ERROR'
        except Exception as exc:
            print('ERROR: Ошибка при работе с CDR. Дальнейшее конвертирование невозможно.'
                  'Причина - %s. Проверьте журнал для получения информации.' % exc)
            self.status['convert'] = 'ERROR'
        else:
            print('COMPLETE: Все CDR файлы успешно сконвертированы.')
            self.status['convert'] = 'DONE'

    def transfer(self):  # Передать сконвертированные файлы на сервер с UTM
        try:
            self.convert()
            if self.status == 'ERROR':
                return

            all_local_paths = []  # Список абсолютных путей к локальным CDR файлам
            for cdr in listdir(self.cdr_converted_dir):
                all_local_paths.append(path.join(self.cdr_converted_dir, cdr))

            if self.status['convert'] == 'DONE' and len(all_local_paths) > 0:
                connect = utm_connect.ServerConnect(self.config)
                connect.cdr_transfer(all_local_paths, self.remote_cdr_dir)
                print('COMPLETE: Все CDR файлы успешно переданы на сервер.')
                self.status['transfer'] = 'DONE'
            else:
                print('ERROR: Сконвертированные CDR файлы недостпуны или не существуют.'
                      'Невозможно отправить CDR файлы на сервер.')
                self.status['transfer'] = 'ERROR'
        except Exception as exc:
            print('ERROR: Ошибка при работе с CDR. Передача файлов невозможна.'
                  'Причина - %s. Проверьте журнал для получения информации.' % exc)
        else:
            pass

    def parse(self):
        #Start parse converted CDR files via utm5_send_cdr

        self.transfer()
        print('INFO: Данная функция в настоящей версии не реализована.')
        count = 1
        if self.status['transfer'] == 'DONE':
            for cdr in listdir(self.cdr_converted_dir):
                try:
                    subprocess.check_output(['ping','www.google.ru'], shell=True)
                except subprocess.CalledProcessError as exc:
                    print('ERROR: Произошла ошибка парсинга. Опреация прервана.\n')
                    return
                print('INFO:  Файл %s успешно пропарсился\n' % (str(count)))
                count += 1
            print('COMPLETE: Все CDR файлы успешно пропарсились.\n')
        else:
            print('ERROR: Невозможно пропарсить CDR файлы на сервере.\n')
