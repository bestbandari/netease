#coding=utf-8
import socket, select
import threading,time
import collections

buf_size = 2048

msg_welcome = '欢迎来到Las Vegas聊天室, 请选择：\n1.注册新用户\n2.登录'
msg_invalid_input = '输入错误，请重新选择'
msg_username= '请输入用户名'
msg_password= '请输入密码'
msg_auth_fail = '用户名密码不匹配'

msg_welcome_lobby = '欢迎%s来到大厅'
msg_welcome_room = '欢迎%s来到房间'

msg_cmd_lobby = '-输入$showroom， 获取房间列表\n-输入$enterroom 房间号， 进入房间\n-输入$createroom， 创建新房间'

msg_info_no_room = '目前没有房间'

msg_err_cmd = '输入指令有误: %s'
msg_err_room_num = '房间号有误'


def welcome(client):
    client.settimeout(500)
    name = None
    
    while name is None :
        client.send(msg_welcome)
        buf = client.recv(buf_size)
        
        if buf == '1':
            signup(client)
            name = login(client)
            
        elif buf == '2':
            name = login(client)
            
        else:
            client.send(msg_invalid_input)
    return name 

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
        return None
        
def authenticate(username, password):
    if 'netease1' in username  and password == '123':
        return True
    return False


class user(object):
    def __init__(self, username, sock, duration):
        self.username = username
        self.sock = sock
        self.duration = duration
        self.stamp = time.clock()
        
    def get_duration(self):
        return duration + time.clock() - self.stamp

class users(object):        
    def __init__(self):
        self.pool = {}
    
    def add_user(self, username, sock, duration):
        self.pool[username] = user(username, sock, duration)
        
    def broadcast(self, msg):
        for user in self.pool.itervalues():
            user.sock.send(msg)

class unit(object):
    LOBBY = None
    USERS = None
    
    def __init__(self):
        self.name_sock = {}
        self.sock_name = {}
        self.roomname = ''
        
        self.cmd = {}
        self.cmd['chat'] = self.chat
        self.cmd['chatall'] = self.chatall
        self.cmd['exit'] = self.exit
        
        self.run()

    def chat(self, data, client):
        msg = '[' + time.ctime()+ '] ' + self.roomname + '-' + self.sock_name[client] + ': ' + data
        unit.LOBBY.broadcast(msg)
        
    def chatall(self, data, client):
        msg = '[' + time.ctime()+ '] ' + '所有人' + '-' + self.sock_name[client] + ': ' + data
        unit.USERS.broadcast(msg)
        
    def exit(self, data, client):
        msg = self.sock_name[client] + ' exit'
        print msg
        self.broadcast(msg)
        client.close()
        self.delete_client(client)
            
    def add_client(self, client, username):
        self.name_sock[username] = client
        self.sock_name[client] = username
        
    def delete_client(self, client):
        name = self.sock_name[client]
        self.sock_name.pop(client)
        self.name_sock.pop(name)
        
    def run(self):
        thread = threading.Thread(target=self.listen, args=())
        thread.daemon = True
        thread.start()        
    
    def listen(self):
        
        
        while 1:
            inputs = [client for client in self.name_sock.itervalues()]
            readyInput,readyOupt,readyException = select.select(inputs,[],[], 1)
            
            for c in readyInput:
                try:
                    data = c.recv(buf_size)
                    self.process(data, c)
                except:
                    c.close()
                    self.delete_client(c)
                
    
    def broadcast(self, msg):
        for sock in self.name_sock.itervalues():
            sock.send(msg)
            
    def process(self, data, client):
        if len(data) == 0:
            client.close()
            self.delete_client(client)
            return
        
        if data[0] == '$':
            self.process_cmd(data, client)
        elif data[0] == '\\':
            pass
        else:
            msg = '[' + time.ctime()+ ']' + self.sock_name[client] + ': ' + data
            self.broadcast(msg)
            
    
    def process_cmd(self, data, client):
        pos = data.find(' ')
        if pos == -1:
            pos = len(data)
        cmd = data[1:pos]
        
        self.cmd[cmd](data[pos+1:], client)
        
class lobby(unit):
    def __init__(self):
        super(lobby, self).__init__()
        self.roomname = '大厅'
        self.rooms = []
        
        self.cmd['showroom'] = self.showroom
        self.cmd['enterroom'] = self.enterroom
        self.cmd['createroom'] = self.createroom
        
        unit.LOBBY = self
        unit.USERS = users()
        
    def showroom(self, data, client):
        msg = ''
        for i, room in enumerate(self.rooms):
            msg += str(i) + '. ' + room.roomname + '\n'
        
        if msg == '':
            msg = msg_info_no_room
        client.send(msg)
        
    def enterroom(self, data, client):
        try:
            num = int(data)
            self.rooms[num].add_client(client, self.sock_name[client])
            self.delete_client(client)
            
        except ValueError:
            msg = msg_err_room_num
            client.send(msg)
        
    def createroom(self, data, client):
        roomname = data
        self.rooms.append(room(roomname))
        self.enterroom(str(len(self.rooms)-1), client)

    def register_client(self, client, username, duration):
        unit.USERS.add_user(username, client, duration)
        self.add_client(client, username)
        
    def add_client(self, client, name):
        super(lobby, self).add_client(client, name)
        msg = msg_welcome_lobby % name
        self.broadcast(msg)
        client.send(msg_cmd_lobby)
        


class room(unit):
    def __init__(self, roomname):
        super(room, self).__init__()
        self.roomname = roomname
        
    def exitroom(self, data, client):
        unit.LOBBY.add_client(client, self.sock_name[client])
        self.delete_client(client)
        
    def add_client(self, client, name):
        super(room, self).add_client(client, name)
        msg = msg_welcome_room % name
        self.broadcast(msg)
        
        