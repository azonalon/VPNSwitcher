from PyQt5 import Qt, QtCore, QtWidgets, uic
import subprocess as sp
from multiprocessing import Pool  
import os, sys
import socket
import psutil
import platform
import threading
from Ping import ping

from os.path import join
try: 
  resources = os.path.split(os.path.abspath(__file__))[0]
except:
  resources = '/home/eduard/programming/VPNSwitcher'
sys.path.append(resources)
with open(join(resources, "select_ui.py"), 'w') as f:
  uic.compileUi(join(resources, "select.ui"), f)
from select_ui import Ui_ServerSelector

def openVPNRunning():
  for proc in psutil.process_iter(attrs=['name']):
    if 'openvpn' in proc.info['name']:
      return True
  return False

HOST = 'localhost'
PORT = '8926'
userpass = '/home/eduard/.vpn_up'
upargs = []
spath = os.path.join(resources, 'servers')
spath = "/etc/openvpn/ovpn_tcp"

if len(userpass) > 0:
  upargs = ['--auth-user-pass', userpass]

class Country(QtWidgets.QTreeWidgetItem):
  # def __lt__(self, other):
  #   try:
  #     return int(self.text(2)) < int(other.text(2))
  #   except:
  #     return self.text(0) < other.text(0)

  def __init__(self, shortcut):
    super().__init__()
    self.shortcut = shortcut
    self.setText(0, shortcut)
    pass
  def __repr__(self):
    return str([self.child(i) for i in range(self.childCount())])

class Server(QtWidgets.QTreeWidgetItem):
  def __lt__(self, other):
    column = self.treeWidget().sortColumn()
    if column == 2:
      return int(self.text(2)) < int(other.text(2))
    return self.text(column).lower() < other.text(column).lower()
  def __init__(self, id, filename):
    super().__init__()
    self.id = id
    self.number = id[2:]
    self.filename = filename
    self.attrs = {}
    self.ping = 9999
    with open(os.path.join(spath, filename)) as f:
      for line in f:
        words = line.split(' ')
        if words[0] == 'remote':
          self.ip = words[1]
          self.port = words[2].replace('\n', '') # there is a newline
          break
    self.setText(0, self.id)
    self.setText(1, self.number)
    self.setText(2, str(self.ping))
  def __repr__(self):
    return self.id
 
# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# try:
#     s.bind((HOST, PORT))
# except socket.error as msg:
#     print ('Bind failed. Error Code : ') + str(msg)
#     sys.exit()
# s.listen(10)
# while 1:
#     # blocking                    
#     conn, addr = s.accept()
#     print ('Connected with ') + addr[0] + ':' + str(addr[1])
# s.close()

def populateTreeWidget(w):
  servers = os.listdir(spath)
  countries = {}
  for s in servers:
    sep = s.split('.')
    server = Server(sep[0], s)
    cid = sep[0][0:2]
    if not cid in countries:
      countries[cid] = Country(cid)
    countries[cid].addChild(server)
  w.addTopLevelItems(countries.values())



def onItemExpansion(item):
  def updatePing(i):
    server = item.child(i)
    p = ping(server.ip)
    server.ping = p*1000 if p is not None else 9999
    print(server.ping)
    server.setText(2, str(int(server.ping)))
  def updatePings():
    for i in range(item.childCount()):
      updatePing(i)
  t = threading.Thread(target=updatePings)
  t.start()


class OpenVPNHandler:  
  def __init__(self):
    self.p=None
    pass

  def connect(self, config):
    if self.p is not None:
      self.disconnect()
    assert not openVPNRunning()
    cmd = ['openvpn',  #'--dev', tun, '--client', 
            '--config', config ,
          ] + upargs
    self.p = sp.Popen(cmd)

  def disconnect(self):
    if self.p is not None:
      self.p.kill()
      ret = self.p.wait(3)
      self.p=None
      assert ret is not None
  def __del__(self):
    if self.p is not None:
      self.p.kill()


if __name__ == "__main__":
  app = QtWidgets.QApplication(sys.argv)
  menu = QtWidgets.QMenu()
  exitAction = Qt.QAction('&Exit')
  showAction = Qt.QAction('&Show')
  exitAction.triggered.connect(lambda: exit(0))
  menu.addAction(exitAction)
  menu.addAction(showAction)
  icon = Qt.QIcon(os.path.join(resources, "icon.png"))
  trayIcon = QtWidgets.QSystemTrayIcon()
  trayIcon.setContextMenu(menu)
  trayIcon.setIcon(icon)
  handler = OpenVPNHandler()
  window = QtWidgets.QDialog()
  window.setWindowTitle("Select a server")
  uiw =  Ui_ServerSelector()
  uiw.setupUi(window)
  showAction.triggered.connect(lambda: window.show())
  def connectSelected():
    it = uiw.treeWidget.currentItem()
    try:
      handler.connect(os.path.join(spath, it.filename))
    except AttributeError:
      print("Select an appropriate item")
  uiw.pushButton.pressed.connect(connectSelected)
  uiw.disconnectButton.pressed.connect(handler.disconnect)
  uiw.hideButton.pressed.connect(lambda: window.hide())
  w = uiw.treeWidget
  w.itemExpanded.connect(onItemExpansion)
  populateTreeWidget(w)
  window.show()
  trayIcon.show()
  sys.exit(app.exec_())
