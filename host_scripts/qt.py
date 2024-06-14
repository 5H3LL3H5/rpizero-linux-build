import sys
import struct
import subprocess

from PyQt5.QtCore import QSize, Qt, QEvent
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene
from keymap import inv_qtkeys, unshift_table, create_key_report

from config import HOST_AND_USER

import atexit
import time

ssh_process = subprocess.Popen(["ssh", HOST_AND_USER, "sudo", "python", "allsync.py"], stdin=subprocess.PIPE, stdout=None, stderr=None)

def handler_exit():
    ssh_process.terminate()
    ssh_process.wait()

atexit.register(handler_exit)

def send_payload(payload):
    ssh_process.stdin.write(payload)
    ssh_process.stdin.flush()

class StateManager():
    def __init__(self):
        self.pressed_keys = set()
        self.pressed_buttons = set()
        self.current_pos = None
        self.current_pos_old = None

        self.key_callback = None
        self.pos_callback = None
        self.button_callback = None
    
    def change_pos(self, p):
        if self.current_pos != p:
            self.current_pos_old = self.current_pos
            self.current_pos = p
            self.pos_callback((self.current_pos_old, self.current_pos, self.pressed_buttons))

    def add_key(self, k):
        if k in unshift_table:
            k = unshift_table[k]
        if not k in self.pressed_keys:
            self.pressed_keys.add(k)
            self.key_callback(self.pressed_keys)
    
    def remove_key(self, k):
        if k in unshift_table:
            k = unshift_table[k]
        if k in self.pressed_keys:
            self.pressed_keys.remove(k)
            self.key_callback(self.pressed_keys)

    def add_button(self, b):
        if not b in self.pressed_buttons:
            self.pressed_buttons.add(b)
            self.button_callback((self.current_pos, self.current_pos, self.pressed_buttons))
    
    def remove_button(self, b):
        if b in self.pressed_buttons:
            self.pressed_buttons.remove(b)
            self.button_callback((self.current_pos, self.current_pos, self.pressed_buttons))

    def set_pos_callback(self, cb):
        self.pos_callback = cb

    def set_key_callback(self, cb):
        self.key_callback = cb

    def set_button_callback(self, cb):
        self.button_callback = cb

sm = StateManager()

def mouse_func(x):
    (oldpos, newpos, btns) = x

    if oldpos != None and newpos != None:
        dx, dy = newpos[0] - oldpos[0], newpos[1] - oldpos[1]
        intersection = btns & {1, 2, 4} # 1: left, 2: right, 4:middle
        payload = struct.pack('<BhhBB', sum(intersection), dx, dy, 0, 0)
        print('pos+btn', payload)
        send_payload(b'\x01' + payload)

def key_func(keys):
    print(keys)
    payload = create_key_report(list(keys))
    # print([inv_qtkeys[k] for k in list(keys)])
    print('key', keys, payload)
    send_payload(b'\x02' + payload)

sm.set_pos_callback(mouse_func)

sm.set_key_callback(key_func)

sm.set_button_callback(mouse_func)

# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("My App")
        self.view = QGraphicsView()
        self.view.setFixedSize(QSize(200,200))
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)

        self.setCentralWidget(self.view)
        # self.setMouseTracking(True)
        self.setFixedSize(QSize(200,200))
    
    def eventFilter(self, source, event):
        if event.type() == QEvent.MouseMove:
            sm.change_pos((event.pos().x(), event.pos().y()))
            return True
        elif event.type() == QEvent.KeyPress:
            sm.add_key(event.key())
            return True
        elif event.type() == QEvent.KeyRelease:
            sm.remove_key(event.key())
            return True
        elif event.type() == QEvent.MouseButtonPress:
            sm.add_button(event.button())
            return True
        elif event.type() == QEvent.MouseButtonRelease:
            sm.remove_button(event.button())
            return True
        return QMainWindow.eventFilter(self, source, event)

app = QApplication(sys.argv)

window = MainWindow()
window.show()
app.installEventFilter(window)

app.exec()
