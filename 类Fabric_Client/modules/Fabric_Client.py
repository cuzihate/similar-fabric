# /usr/bin/env python
# coding:utf-8
# author:ZhaoHu

import socket
import json
import os
import sys
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import commons
from multiprocessing import Pool

ip_port_list = [('172.16.111.130', 10086), ('172.16.111.131', 10086)]
# ip_port_list = [('127.0.0.1', 10098), ]
socket_obj = socket.socket()

def view_bar(current_size, total_size):
    rate = current_size / total_size
    rate_num = int(rate * 100)
    print('file transporting ... | %-25s | \033[31;1m%3d%%\033[0m' % ('>' * (rate_num // 4), rate_num), end='\r')
    time.sleep(0.01)

def put(ip_port, user_input):
    socket_obj.connect(ip_port)
    while True:
        if user_input == 'q':
            break
        cmd_list = user_input.split()
        if len(cmd_list) < 2:
            print('\033[31;1m命令不合法\033[0m')
            break
        if cmd_list[0] == 'put':
            if os.path.exists(cmd_list[1]):  # 本地文件存在
                file_name = cmd_list[1].split(os.sep)[-1]
                file_size = os.stat(cmd_list[1]).st_size
                file_md5 = commons.get_file_md5(cmd_list[1])
                print('file:%s, size: %s, md5: %s' % (file_name, file_size, file_md5))
                file_info = {'action': 'put', 'filename': file_name, 'filesize': file_size, 'filemd5': file_md5}
                socket_obj.sendall(bytes(json.dumps(file_info), encoding='utf-8'))  # 将文件相关信息发送给服务器
                notify_info = json.loads(socket_obj.recv(1024).decode())  # 接收服务器的通知消息
                current_size = notify_info.get('current_size')  # 服务端已存在文件大小，不存在为0 --》断点续传
                server_ip = notify_info.get('ip').strip()
                if notify_info.get('stat') == 'ok':
                    with open(cmd_list[1], 'rb') as file:
                        file.seek(current_size)  # 断点续传
                        for line in file:
                            socket_obj.sendall(line)
                            current_size += len(line)
                            view_bar(current_size, file_size)  # 调用进度条
                    print('\033[31;1m%s Mission complate ..\033[0m' % server_ip)
                    send_success_msg = socket_obj.recv(1024).decode()
                    print(send_success_msg)
                    break
                else:
                    print('\033[31;1mServer %s file exists\033[0m' % server_ip)
                    break
            else:
                print('\033[31;1m本地文件 %s 不存在\033[0m' % cmd_list[1])
                break
        else:
            print('\033[31;1m命令不合法\033[0m')
            break

def file_recv(file_name, file_md5, file_size, current_size, write_method):
    notify_info = {'current_size': current_size, 'stat': 'ok'}
    socket_obj.sendall(bytes(json.dumps(notify_info), encoding='utf-8'))  # ask server to start transport file
    with open(file_name, write_method) as new_file:  # 接收写文件
        recv_size = current_size
        while recv_size < file_size:
            data = socket_obj.recv(4096)
            recv_size += len(data)
            new_file.write(data)
            view_bar(recv_size, file_size)
        print('%s receive successful' % file_name)
    local_file_md5 = commons.get_file_md5(file_name)
    print('本地 %s | 服务器 %s' % (local_file_md5, file_md5))
    if local_file_md5 == file_md5:
        msg = '\033[31;1mThe file in server and the local file are just the same\033[0m'
        socket_obj.sendall(bytes(msg, encoding='utf-8'))
        print(msg)
    else:
        msg = '\033[31;1mThe file in server and the local file are different\033[0m'
        socket_obj.sendall(bytes(msg, encoding='utf-8'))
        print(msg)
def get(ip_port, user_input):
    socket_obj.connect(ip_port)
    while True:
        if user_input == 'q':
            break
        cmd_list = user_input.split()
        if len(cmd_list) != 2:
            print('\033[31;1m命令不合法\033[0m')
            break
        if cmd_list[0] == 'get':
            file_info = {'action': 'get', 'filename': cmd_list[1]}
            socket_obj.sendall(bytes(json.dumps(file_info), encoding='utf-8'))  # 通知服务器调用get方法
            exist_or_not = json.loads(socket_obj.recv(1024).decode())  # 接收服务端通知
            if exist_or_not.get('exist') == 'no':  # 服务端文件不存在
                server_ip = exist_or_not.get('ip').strip()
                print('\033[31;1mServer %s file not exist!\033[0m' % server_ip)
                break
            else:
                file_name = exist_or_not.get('filename')
                file_size = exist_or_not.get('filesize')
                file_md5 = exist_or_not.get('filemd5')
                print('文件 %s 大小为 %s md5 %s' % (cmd_list[1], file_size, file_md5))
                if not os.path.exists(file_name):  # 服务端文件存在，本地不存在
                    file_recv(file_name, file_md5, file_size, 0, 'wb')  # 直接 w 写
                    break
                else:
                    exist_file_size = os.stat(file_name).st_size  # 本地存在文件大小
                    if exist_file_size < file_size:
                        print('\033[31;1mfile %s exist, but incomplete! size: %s\033[0m' % (file_name, exist_file_size))
                        file_recv(file_name, file_md5, file_size, exist_file_size, 'ab')  # 断点续传，a 追加模式
                        break
                    else:
                        notify_info = {'stat': 'no'}  # 本地文件完整，通知服务端无需操作
                        socket_obj.sendall(bytes(json.dumps(notify_info), encoding='utf-8'))
                        print('\033[31;1mfile %s already exist now, size: %s\033[0m' % (file_name, exist_file_size))
                        break
        else:
            print('\033[31;1m命令不合法\033[0m')
            break

def run_cmd(ip_port, user_input):
    socket_obj.connect(ip_port)
    while True:
        if user_input == 'q':
            break
        cmd_list = user_input.split()
        if not cmd_list or len(cmd_list) > 2:
            print('\033[31;1m命令不合法\033[0m')
            break
        else:  # 只有长度为2的命令才会发送给服务端
            cmd_info = {'action': cmd_list[0], 'cmd': user_input}
            socket_obj.sendall(bytes(json.dumps(cmd_info), encoding='utf-8'))
            result_info = json.loads(socket_obj.recv(1024).decode())  # 接收服务端回复
            if result_info.get('tag') == 'failed':
                server_ip = result_info.get('ip')
                print('\033[31;1m%s输入命令有误或不支持，请重新输入\033[0m' % server_ip)
                break
            else:
                result_len = result_info.get('result_len')
                socket_obj.sendall(bytes('start to trans..', encoding='utf-8'))  # 通知服务端发送数据
                recv_size = 0
                recv_msg = b''
                while recv_size < result_len:  # 循环接收数据，防止黏包
                    recv_data = socket_obj.recv(1024)
                    recv_msg += recv_data
                    recv_size += len(recv_data)
                print(recv_msg.decode())
                break

menu_dict = {
    '1': put,
    '2': get,
    '3': run_cmd
}

def welcome(ip_port):
    socket_obj.connect(ip_port)
    cmd_info = {'action': 'connect'}
    socket_obj.sendall(bytes(json.dumps(cmd_info), encoding='utf-8'))
    welcome_msg = socket_obj.recv(1024).decode()
    print('已经连接上 %s 主机，请进行下一步操作~' % welcome_msg.strip())
    socket_obj.sendall(bytes('已经建立连接啦~', encoding='utf-8'))

def main():
    flag = True
    while flag:
        server_group = []
        print('当前主机组：%s' % ip_port_list)
        usr_inp = commons.input2('请输入您要操作的主机或者主机组（默认为主机组）:', default=ip_port_list)
        if usr_inp not in ip_port_list and usr_inp != ip_port_list:
            print('请按照规则输入：(xxx)')
            continue
        if type(usr_inp) == tuple:
            server_group.append(usr_inp)
        else:
            server_group = usr_inp
        # print(server_group)
        pool = Pool(5)
        for server_ip in server_group:
            pool.apply_async(func=welcome, args=(server_ip, ))
        pool.close()
        pool.join()
        while True:
            user_choice = input('1、上传 | 2、下载 | 3、执行命令 | q选项退出: ').strip()
            if user_choice in menu_dict:
                pool = Pool(5)
                user_input = input('输入需要执行的命令 : ').strip()
                for server_ip in server_group:
                    pool.apply_async(func=menu_dict.get(user_choice), args=(server_ip, user_input, ))
                pool.close()
                pool.join()
            elif user_choice == 'q':
                print('bye~')
                flag = False
                break
            else:
                print("请按照规则输入！！")


if __name__ == '__main__':
    main()