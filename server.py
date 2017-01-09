#coding=utf-8 
import socket
import threading,getopt,sys,string

from chat import *

opts, args = getopt.getopt(sys.argv[1:], "hp:m:",["help","port=","max_connection="])
#设置默认的最大连接数和端口号，在没有使用命令传入参数的时候将使用默认的值
max_connection=50
host = 'localhost'
port=8888

LOBBY = lobby()
LOBBY.run()

def usage():
    print """
    -h --help             print the help
    -m --max_connection             Maximum number of connections
    -p --port             To monitor the port number  
    """
for op, value in opts:
    if op in ("-m","--max_connection"):
        max_connection = string.atol(value)
    elif op in ("-p","--port"):
        port = string.atol(value)
    elif op in ("-h"):
        usage()
        sys.exit()


def newConnection(client):
    username = welcome(client)
    LOBBY.add_client(client, username)

def main():

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  

    sock.bind((host, port))

    sock.listen(max_connection) 
    while True:  
        client,address = sock.accept()  
        print '%s connected' % address[0]
        thread = threading.Thread(target=newConnection, args=(client,))
        thread.start()



if __name__ == '__main__':
    main()