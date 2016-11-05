# PS.本类Fabric程序在上节作业FTP程序上的修改，阉割了部分功能，仅保留了上传、下载及执行部分命令

 - 客户端与服务端分离，服务端在ubuntu的Pycharm上执行通过

 - 客户端使用进程池来进行对服务器或服务器组的连接，服务器组定义在 ip_port_list 列表中

 - 服务端支持的命令有：
	ls/dir/du/df/uname/pwd/ifconfig
