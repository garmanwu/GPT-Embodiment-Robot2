import os
import socket
import time
import json
import threading
from scene import *
from sound import play_effect
from ast import literal_eval

IP_ADDR = '0.0.0.0'  
PORT1 = 7895
PORT2 = 7896

class MyScene(Scene):
    def setup(self):
        self.background_color = 'black'
        self.lyrics_text = LabelNode('', font=('Helvetica', 18), color='gray', position=(self.size.w/2, 50), parent=self)
        self.kaomoji_text = LabelNode('', font=('Helvetica', 120), color='white', position=(self.size.w/2, self.size.h/2), parent=self)

    def update(self):
        pass

    def touch_began(self, touch):
        os._exit(0)

    def did_change_size(self):
        pass

def receive_audio():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((IP_ADDR, PORT1))
        s.listen()
        while True:
            conn, addr = s.accept()
            with conn:
                data = b''
                while True:
                    chunk = conn.recv(1024)
                    if not chunk:
                        break
                    data += chunk
                timestamp = int(time.time())
                file_path = f'audio_{timestamp}.mp3'
                with open(file_path, 'wb') as f:
                    f.write(data)
                play_effect(file_path)

def receive_lyrics():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((IP_ADDR, PORT2))
        s.listen()
        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(1024).decode()
                data_dict = literal_eval(data)
                lyrics = data_dict.get('lyrics', '')
                kaomoji = data_dict.get('kaomoji', '')
                
                # 对歌词进行过滤处理
                lyrics = lyrics.replace('\\n', ' ').replace('\n', ' ')
                lyrics = ' '.join(lyrics.split())
                
                # 对表情符号进行长度检查和截断
                max_length = 10
                if len(kaomoji) > max_length:
                    kaomoji = kaomoji[:max_length] + '...'
                
                scene.lyrics_text.text = lyrics
                scene.kaomoji_text.text = kaomoji

scene = MyScene()

audio_thread = threading.Thread(target=receive_audio)
audio_thread.daemon = True
audio_thread.start()

lyrics_thread = threading.Thread(target=receive_lyrics)
lyrics_thread.daemon = True
lyrics_thread.start()

run(scene, orientation=LANDSCAPE)