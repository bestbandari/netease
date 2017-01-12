#coding=utf-8
import socket, select
import threading,time
import collections, random
import re
import sqlite3
from datetime import timedelta

buf_size = 2048

db_file = 'mydb.db'
admin = 'Administrator'

msg_welcome = 'Welcome to Las Vegas chat room. Please select：\n1.sign in\n2.sign up.'
msg_username= 'Please enter your user name.'
msg_password= 'Please enter your password.'
msg_password_again = 'Please confirm your password.'
msg_auth_fail = 'Your user name and password do not match.'
msg_signup_success = 'Success! Please login to the Lobby.'

msg_welcome_lobby = 'Welcome %s to Lobby\n'
msg_welcome_room = 'Welcome %s to our room.'

msg_cmd_lobby = '-$showroom， get a list of exsting rooms\n' + '-$enterroom #room number#， enter an exsting room\n' + '-$createroom， create a new room'

msg_info_no_room = 'There is no room. You can create one.'
msg_info_exit_room = '%s exit room.'
msg_info_res_accept = 'Your answer is %d.'
msg_info_winner = '21 game ended. The winner is %s. The result is %s. Congratulations!'
msg_info_no_winner = 'There is no winner.'
msg_info_pos_dura = 'Your location: %s. Your total online time: %s.'


msg_err_cmd = 'Invalid command: %s.'
msg_err_room_num = 'Invalid room number.'
msg_err_21_end = '21 game has ended. Please wait for the next round.'
msg_err_invalid_input = 'Invalid input, enter again.'
msg_err_invalid_user = '%s is not online or does not exist.'
msg_err_empty_msg = 'You send an empty message.'
msg_err_empty_room_name = 'Room name cannot be empty.'
msg_err_pass_not_match = 'Passwords do not match. Please try again.'
msg_err_user_exist = 'Your user name exists. Please enter another name.'
msg_err_user_logged_in = 'You\'ve logged in. Please log out on the other terminal first.'


class mydb(object):
    def __init__(self):
        self.conn = sqlite3.connect(db_file)
        self.c = self.conn.cursor()
    
    def __del__(self):
        self.conn.commit()
        self.conn.close()
        
    def check_username(self, username):
        self.c.execute('select * from users where username=?', (username,))
        
        return bool(self.c.fetchone())
    
    def create_user(self, username, password):
        self.c.execute('INSERT INTO users VALUES (?,?,?)', (username, str(password), 0))

    def authenticate(self, username, password):
        self.c.execute('select * from users where username=? and password=?',\
                       (username, str(password)))
        
        return bool(self.c.fetchone())
        
    def get_duration(self, username):
        self.c.execute('select duration from users where username=?', (username,))
        return int(self.c.fetchone()[0]) 
    
    def set_duration(self, username, duration):
        self.c.execute('update users set duration=? where username=?', (duration,username))
        

def welcome(client):
    client.settimeout(500)
    name = None
    
    while name is None :
        client.send(msg_welcome)
        buf = client.recv(buf_size)
        
        if buf == '1':
            name = login(client)
            
        elif buf == '2':
            signup(client)
            name = login(client)
            
        else:
            client.send(msg_err_invalid_input)
    return name 

def signup(client):
    DB = mydb()
    
    while 1:
        client.send(msg_username)
        username = client.recv(buf_size)
        
        if DB.check_username(username):
            client.send(msg_err_user_exist)
            continue
        
        client.send(msg_password)
        password1 = client.recv(buf_size)
        
        client.send(msg_password_again)
        password2 = client.recv(buf_size)    
        
        if password1 == password2:
            DB.create_user(username, hash(password1))
            client.send(msg_signup_success)
            break
        
        client.send(msg_username)

def login(client):
    DB = mydb()
    
    client.send(msg_username)
    username = client.recv(buf_size)
    
    client.send(msg_password)
    password = client.recv(buf_size)
    
    if DB.authenticate(username, hash(password)):
        if lobby.USERS.exist(username):
            client.send(msg_err_user_logged_in)
            return None
        else:
            return username
    else:
        client.send(msg_auth_fail)
        return None
      

def build_msg(source, user, msg):
    return '[' + time.ctime()+ ']' + '<' + source + '> ' + user + ': ' + msg

class user(object):
    def __init__(self, username, sock, duration):
        self.username = username
        self.sock = sock
        self.duration = duration
        self.stamp = time.time()
        
    def send_msg(self,msg):
        self.sock.send(msg)
    
    def get_duration(self):
        return self.duration + time.time() - self.stamp
    
    def set_duration(self):
        DB = mydb()
        DB.set_duration(self.username, self.get_duration())

class users(object):        
    def __init__(self):
        self.pool = {}
    
    def exist(self, username):
        return username in self.pool
    
    def add_user(self, username, sock, duration):
        self.pool[username] = user(username, sock, duration)
        
    def send_msg(self, username, msg):
        self.pool[username].send_msg(msg)
        
    def broadcast(self, msg):
        for user in self.pool.itervalues():
            user.sock.send(msg)
            
    def get_duration(self, username):
        return self.pool[username].get_duration()
    
    def delete_user(self, username):
        self.pool[username].set_duration()
        self.pool.pop(username)

class unit(object):
    LOBBY = None
    USERS = None
    
    def __init__(self):
        self.name_sock = {}
        self.sock_name = {}
        self.roomname = ''
        
        self.cmd = {}
        self.cmd['help'] = self.help
        self.cmd['info'] = self.info
        self.cmd['chat'] = self.chat
        self.cmd['chatall'] = self.chatall
        self.cmd['exit'] = self.exit
        
        self.run()
        
    def help(self, data, client):
        s = []
        for i, cmd in enumerate(self.cmd):
            s.append(str(i) + '. $' + cmd)
        
        client.send('\n'.join(s))
        
    def info(self, data, client):
        duration = timedelta(seconds=unit.USERS.get_duration(self.sock_name[client]))
        
        msg = msg_info_pos_dura % (self.roomname, str(duration))
        
        client.send(msg)
        
    def chat(self, data, client):
        if len(data) > 0:
            msg = build_msg(unit.LOBBY.roomname, self.sock_name[client], data)
            unit.LOBBY.broadcast(msg)
        else:
            msg = build_msg(unit.LOBBY.roomname, admin, msg_err_empty_msg)
            client.send(msg)            
            
        
    def chatall(self, data, client):
        if len(data) > 0:
            msg = build_msg('ALL', self.sock_name[client], data)
            unit.USERS.broadcast(msg)
        else:
            msg = build_msg('ALL', admin, msg_err_empty_msg)
            client.send(msg)          
        
    def exit(self, data, client):
        msg = build_msg(self.roomname, admin, self.sock_name[client] + ' exit')
        print msg
        self.broadcast(msg)
        unit.USERS.delete_user(self.sock_name[client])
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
        elif data[0] == '/':
            self.private_msg(data, client)
        else:
            msg = build_msg(self.roomname, self.sock_name[client], data)
            self.broadcast(msg)
            
    def process_cmd(self, data, client):
        pos = data.find(' ')
        if pos == -1:
            pos = len(data)
        cmd = data[1:pos]
        
        if cmd in self.cmd:
            self.cmd[cmd](data[pos+1:], client)
        else:
            msg = msg_err_cmd % cmd
            client.send(msg)
        
    def private_msg(self, data, client):
        pos = data.find(' ')
        if pos == -1 or pos == len(data)-1:
            msg = build_msg(self.roomname, admin, msg_err_empty_msg)
            client.send(msg)            
            return
        
        recipent = data[1:pos]
        if recipent not in unit.USERS.pool:
            msg = build_msg(self.roomname, admin, msg_err_invalid_user % recipent)
            client.send(msg)
            return
        
        msg = build_msg('Private message', self.sock_name[client], data[pos+1:])
        unit.USERS.send_msg(recipent, msg)
    
class lobby(unit):
    def __init__(self):
        super(lobby, self).__init__()
        self.roomname = 'Lobby'
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
            msg = build_msg(self.roomname, admin, msg_info_no_room)
        client.send(msg)
        
    def enterroom(self, data, client):
        try:
            num = int(data)
            self.rooms[num].add_client(client, self.sock_name[client])
            self.delete_client(client)
            
        except ValueError:
            msg = build_msg(self.roomname, admin, msg_err_room_num)
            client.send(msg)
        
    def createroom(self, data, client):
        if len(data) == 0:
            msg = build_msg(self.roomname, admin, msg_err_empty_room_name)
            client.send(msg)    
            return 
        
        roomname = data
        self.rooms.append(room(roomname))
        self.enterroom(str(len(self.rooms)-1), client)

    def register_client(self, client, username):
        DB = mydb()
        duration = DB.get_duration(username)
        unit.USERS.add_user(username, client, duration)
        self.add_client(client, username)
        
    def add_client(self, client, name):
        super(lobby, self).add_client(client, name)
        msg = build_msg(self.roomname, admin, msg_welcome_lobby % name)
        self.broadcast(msg)
        client.send(msg_cmd_lobby)
        


class room(unit):
    def __init__(self, roomname):
        super(room, self).__init__()
        self.roomname = roomname
        
        self.cmd['exitroom'] = self.exitroom
        self.cmd['21game'] = self.game21
        
        self.nums = None
        self.winner = ''
        self.res = -40
        self.game_end = True
        threading.Timer(1.0, self.run21game, args=()).start()

        
    def game21(self, data, client):
        if self.game_end:
            msg = build_msg(self.roomname, admin, msg_err_21_end)
            client.send(msg)
            return 
        
        res, valid = self.parse(data)
        if not valid:
            msg = build_msg(self.roomname, admin, msg_err_invalid_input)
            client.send(msg)
            return
        else:
            msg = build_msg(self.roomname, admin, msg_info_res_accept % res)
            client.send(msg)
            
        if res == 21 or self.res < res:
            self.res = res
            self.winner = self.sock_name[client]
            if res == 21:
                self.end21game()

            
    def exitroom(self, data, client):
        msg = build_msg(self.roomname, admin, msg_info_exit_room % self.sock_name[client])
        self.broadcast(msg)        
        unit.LOBBY.add_client(client, self.sock_name[client])
        self.delete_client(client)
        
    def add_client(self, client, name):
        super(room, self).add_client(client, name)
        msg = build_msg(self.roomname, admin, msg_welcome_room % name)
        self.broadcast(msg)
    
    def parse(self, s):
        nums = []
        oper = set(['+', '-', '*', '/'])
        for i in xrange(len(s)):
            c = s[i]
            if c.isdigit():
                if i<len(s)-1 and s[i+1].isdigit():
                    nums.append(s[i:i+2])
                    i+=1
                else:
                    nums.append(s[i])
            elif c in oper:
                continue
            else:
                return -40, False
            
        nums = sorted(nums)
        
        if nums != self.nums:
            return -40, False

        try:
            v = eval(s)
        except:
            return -40, False
        
        return v, True
        
        
    def end21game(self):
        if self.game_end:
            return
        
        self.game_end = True
        if self.winner == '':
            msg = build_msg(self.roomname, admin, msg_info_no_winner)
        else:
            msg = build_msg(self.roomname, admin, msg_info_winner % (self.winner, self.res))
            
        self.broadcast(msg)
            
    def run21game(self):
        t = time.localtime(time.time())
        if t.tm_sec == 0 or t.tm_sec == 30:
            self.winner = ''
            self.res = -40
            self.game_end = False
            
            threading.Timer(15.0, self.end21game, args=()).start()
            
            self.nums = sorted([ str(random.randint(1,10)) for i in xrange(4)])
            
            msg = build_msg(self.roomname, admin, '21 game start: ' + ','.join(self.nums))
            self.broadcast(msg)
        
        threading.Timer(1.0, self.run21game, args=()).start()
        
    