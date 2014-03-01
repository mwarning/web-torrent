
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
from PyQt4.QtNetwork import *

''' Debug window for the DHT '''

class DhtView(QDialog):
	
	def __init__(self, controller, parent=None):
		super(DhtView, self).__init__(parent)
		
		self.setWindowTitle("DhtViewer - Debug")
		
		self.controller = controller
		self.inputLine = QLineEdit()
		self.inputLine.setFixedWidth(120)
		layout = QVBoxLayout()
		
		layout.addWidget(self.inputLine)
		
		self.setLayout(layout)
		self.setWindowTitle("DHT Lookups")
		
		self.inputLine.returnPressed.connect(self.start_dht_lookup)
	
	def start_dht_lookup(self):
		text = self.inputLine.text()
		controller.dht_lookup(text)