#coding=utf-8
import socket, select
import threading,time

buf_size = 2048

msg_welcome = '欢迎来到Las Vegas聊天室, 请选择：\n1.注册新用户\n2.登录'
msg_invalid_input = '输入错误，请重新选择'
msg_username= '请输入用户名'
msg_password= '请输入密码'
msg_auth_fail = '用户名密码不匹配'

msg_welcome_lobby = '欢迎%s来到大厅'
msg_welcome_room = '欢迎%s来到房间'

msg_cmd_lobby = '-输入$showroom， 获取房间列表\n-输入$enterroom 房间号， 进入房间\n-输入$createroom， 创建新房间'

def welcome(client):
    client.settimeout(500)
    buf = ''
    
    while 1:
        client.send(msg_welcome)
        buf = client.recv(buf_size)
        
        if buf == '1':
            signup(client)
            return login(client)
            
        elif buf == '2':
            return login(client)
            
        else:
            client.send(msg_invalid_input)


def signup(client):
    pass

def login(client):
    client.send(msg_username)
    username = client.recv(buf_size)
    
    client.send(msg_password)
    password = client.recv(buf_size)
    
    if authenticate(username, password):
        return username
    else:
        client.send(msg_auth_fail)
        return welcome(client)
        
def authenticate(username, password):
    if 'netease1' in username  and password == '123':
        return True
    return False




class unit(object):
    def __init__(self):
        self.name_sock = {}
        self.sock_name = {}
        
    def add_client(self, client, username):
        self.name_sock[username] = client
        self.sock_name[client] = username
        
    def delete_client(self, client):
        name = self.sock_name[client]
        self.sock_name.pop(client)
        self.name_sock.pop(name)
        
    def run(self):
        thread = threading.Thread(target=self.listen, args=())
        thread.start()        
    
    def listen(self):
        
        
        while 1:
            inputs = [client for client in self.name_sock.itervalues()]
            readyInput,readyOupt,readyException = select.select(inputs,[],[], 1)
            
            for c in readyInput:
                try:
                    data = c.recv(buf_size)
                except:
                    self.delete_client(c)
                self.process(data, c)
    
    def broadcast(self, msg):
        for sock in self.name_sock.itervalues():
            sock.send(msg)
            
    def process(self, data, c):
        if data[0] == '$':
            pass
        elif data[0] == '\\':
            pass
        else:
            msg = '[' + time.ctime()+ ']' + self.sock_name[c] + ': ' + data
            self.broadcast(msg)
            
            
class lobby(unit):

        
    def add_client(self, client, name):
        super(lobby, self).add_client(client, name)
        msg = msg_welcome_lobby % name
        self.broadcast(msg)
        client.send(msg_cmd_lobby)
        


class room(unit):
    def __init__(self, roomname):
        super(lobby, self).__init__()
        self.roomname = roomname
        
        
    def add_client(self, client, name):
        super(lobby, self).add_client(client, name)
        msg = msg_welcome_room % name
        self.broadcast(msg)
        
        