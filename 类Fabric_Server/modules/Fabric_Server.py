# /usr/bin/env python
# coding:utf-8
# author:ZhaoHu

import socketserver
import os
import sys
import json
import subprocess
# import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import commons

ip_port = ('0.0.0.0', 10098)

class MyServer(socketserver.BaseRequestHandler):

    def file_recv(self, file_name, file_md5, file_size, current_size, write_method):
        """
        receive file
        :param file_name: file name
        :param file_size: file size
        :param current_size: current file szie
        :param write_method: the method of write file
        :return:
        """
        notify_info = {'current_size': current_size, 'stat': 'ok', 'ip': self.ip.decode()}
        self.request.sendall(bytes(json.dumps(notify_info), encoding='utf-8'))  # ask client to start transport file
        with open(file_name, write_method) as new_file:
            recv_size = current_size
            while recv_size < file_size:
                data = self.request.recv(4096)
                recv_size += len(data)
                new_file.write(data)
            print('%s receive successful' % file_name)
        local_md5 = commons.get_file_md5(file_name)
        print('本地 %s | 客户端 %s' % (local_md5, file_md5))
        if local_md5 == file_md5:
            msg = '\033[31;1mThe file in server and the local file are just the same\033[0m'
            self.request.sendall(bytes(msg, encoding='utf-8'))
            print(msg)
        else:
            msg = '\033[31;1mThe file in server and the local file are different\033[0m'
            self.request.sendall(bytes(msg, encoding='utf-8'))
            print(msg)

    def task_put(self, file_info):
        """
        upload file
        :param file_info: about file info
        :return:
        """
        file_name = file_info.get('filename')
        file_size = file_info.get('filesize')
        file_md5 = file_info.get('filemd5')
        print(file_name, file_size, file_md5)
        if not os.path.exists(file_name):  # local file not exist, 'w' mode to write
            self.file_recv(file_name, file_md5, file_size, 0, 'wb')
        else:
            current_file_size = os.stat(file_name).st_size
            print('file exist~, current_size:', current_file_size)
            if current_file_size < file_size:  # local file exist but not complete, 'a' mode to write
                self.file_recv(file_name, file_md5, file_size, current_file_size, 'ab')
            else:  # file complete, only notify client
                notify_info = {'current_size': current_file_size, 'stat': 'no', 'ip': self.ip.decode()}
                self.request.sendall(bytes(json.dumps(notify_info), encoding='utf-8'))

    def task_get(self, file_info):
        """
        download file
        :param file_info: about file info
        :return:
        """
        abs_file_path = file_info.get('filename')  # server file abs path
        if not os.path.exists(abs_file_path):  # file not exist
            exist_or_not = {'exist': 'no', 'ip': self.ip.decode()}
            self.request.sendall(bytes(json.dumps(exist_or_not), encoding='utf-8'))
        else:
            file_size = os.stat(abs_file_path).st_size
            file_name = self.ip.decode().strip() + '_' + abs_file_path.split(os.sep)[-1]
            file_md5 = commons.get_file_md5(abs_file_path)
            print(file_name, file_size, file_md5)
            exist_or_not = {'exist': 'yes', 'filename': file_name, 'filesize': file_size, 'filemd5': file_md5}
            self.request.sendall(bytes(json.dumps(exist_or_not), encoding='utf-8'))  # send file info to client
            notify_info = json.loads(self.request.recv(1024).decode())  # receive client notify info
            if notify_info.get('stat') == 'ok':
                with open(abs_file_path, 'rb') as file:
                    file.seek(notify_info.get('current_size'))
                    for line in file:
                        self.request.sendall(line)
                print('\033[31;1mMission complate .. \033[0m')
                send_success_msg = self.request.recv(1024).decode()
                print(send_success_msg)
            else:
                print('\033[31;1mclient file already exists\033[0m')

    def task_mission(self, file_info):
        """
        for some cmd which need to judge user_home_dir
        :param cmd:
        :return:
        """
        cmd = file_info.get('cmd')
        result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        result = result.stdout.read()
        result = self.ip.decode() + result.decode()
        result = bytes(result, encoding='utf-8')
        if not result:
            result_info = json.dumps({'tag': 'null'})
            self.request.sendall(bytes(result_info, encoding='utf-8'))
        else:
            result_info = json.dumps({'result_len': len(result)})
            self.request.sendall(bytes(result_info, encoding='utf-8'))
            start_tag = self.request.recv(1024).decode()
            if start_tag.startswith('start'):
                self.request.sendall(result)
            print('send all successfully')

    def task_ls(self, file_info):
        self.task_mission(file_info)

    def task_dir(self, file_info):
        self.task_mission(file_info)

    def task_du(self, file_info):
        self.task_mission(file_info)

    def task_df(self, file_info):
        self.task_mission(file_info)

    def task_uname(self, file_info):
        self.task_mission(file_info)

    def task_ifconfig(self, file_info):
        self.task_mission(file_info)

    def task_pwd(self, file_info):
        self.task_mission(file_info)

    def handle(self):
        """
        handle method, first to run
        :return:
        """
        get_server_ip = '/sbin/ifconfig|grep "inet addr"|grep -v 127.0.0.1|sed -e "s/^.*addr://;s/Bcast.*$//"'
        result = subprocess.Popen(get_server_ip, shell=True, stdout=subprocess.PIPE)
        self.ip = result.stdout.read()
        while True:
            task_data = self.request.recv(1024).decode()
            if not task_data:
                continue
            print('\033[31;1mBegin Again !! task_data not null !!\033[0m')
            task_data = json.loads(task_data)
            if task_data.get('action') == 'connect':
                self.request.sendall(self.ip)
                client_msg = self.request.recv(1024).decode()
                print('\033[33;1m%s\033[0m' % client_msg)
            else:
                if hasattr(self, 'task_%s' % task_data.get('action')):
                    user_action = getattr(self, 'task_%s' % task_data.get('action'))
                    user_action(task_data)
                    continue
                else:
                    result_info = json.dumps({'tag': 'failed', 'ip': self.ip.decode()})
                    self.request.sendall(bytes(result_info, encoding='utf-8'))
                    continue

if __name__ == '__main__':
    server = socketserver.ThreadingTCPServer(ip_port, MyServer)
    server.serve_forever()
