#coding=utf-8 
import threading,sys
import socket

HOST = 'localhost'
PORT = 8888
buf_size = 2048
addr = (HOST,PORT)

client = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
client.connect(addr)

running = 1


def send_msg(client):
    while True:
        data = raw_input()
        if data == 'exit':
            client.close()
            exit(0)
        
        client.sendall(data)

def recv_msg(client):
    while True:
        try:
            data = client.recv(1024)
            print(data)
        except:
            client.close()
            exit(0)

threading.Thread(target=send_msg, args=(client,)).start()  
threading.Thread(target=recv_msg, args=(client,)).start()
