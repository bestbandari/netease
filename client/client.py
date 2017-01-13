#coding=utf-8 
import threading,sys
import socket, time

HOST = 'localhost'
PORT = 8888
buf_size = 2048
addr = (HOST,PORT)

client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
client.connect(addr)

running = True 


def send_msg(client,th):
    global running
    while running:
        sys.stdout.write('>')
        sys.stdout.flush()
        data = raw_input()
        if data == '$exit':
            client.send(data)
            client.close()
            running = False
            exit(0)
        
        client.send(data)

def recv_msg(client):
    global running
    while running:
        try:
            data = client.recv(1024)
            print '\r' + data
            sys.stdout.write('>')
            sys.stdout.flush()
        except:
            client.close()
            running = False
            exit(0)

th1 = threading.Thread(target=recv_msg, args=(client,))
th1.daemon = True
th1.start()

th2 = threading.Thread(target=send_msg, args=(client,th1))
th2.daemon = True
th2.start()

while running:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        client.send('$exit')
        client.close()
        running = False
