
from PyQt4.QtGui import *
from PyQt4.QtCore import *


''' Debug window for torrent downloads '''

def formatName(d):
	return d.name()

def formatProgress(d):
	return "{}%".format(d.progress())

def formatStatus(d):
	return d.status()

def formatSpeed(d):
	return ('%.1f / %.1f' % (d.download_rate(), d.upload_rate()))

def formatPeerInfo(d):
	return "{} / {}".format(d.num_peers(), d.num_seeds())
	

class TorrentView(QTreeWidget):

	def __init__(self, controller, parent=None):
		super(TorrentView, self).__init__(parent)
		
		self.setWindowTitle("TorrentViewer - Debug")
		self.setSelectionBehavior(QAbstractItemView.SelectRows)
		self.setSortingEnabled(True)
		self.setAlternatingRowColors(False)
		
		self.controller = controller
		controller.download_added.connect(self.addDownload)
		controller.download_removed.connect(self.removeDownload)
		
		self.header_names = ["Name", "Progress", "Speed", "Status", "Peers/Seeds"]
		self.header_funcs = [formatName, formatProgress, formatSpeed, formatStatus, formatPeerInfo]
		self.jobs = list()
		
		self.setHeaderLabels(self.header_names)
		self.setWindowTitle("Torrent Downloads")

		self.setSelectionBehavior(QAbstractItemView.SelectRows)
		self.setAlternatingRowColors(True)
		self.setRootIsDecorated(False)

		#self.setContextMenuPolicy(Qt.ActionsContextMenu)
		self.pos = None
	
	def mousePressEvent(self, event):
		print("mousePressEvent")
		self.pos = event.pos()
		
		if event.button() & Qt.RightButton:
			item = self.itemAt(self.pos)
			if not item: return
			
			row = self.indexOfTopLevelItem(item)
			if row < 0: return
			
			self.selected_download = self.jobs[row]
			
			event.accept()
			menu = QMenu(self)
			
			removeAction = menu.addAction("Remove")
			removeAction.triggered.connect(self.removeDownloadSelected)
			
			pauseAction = menu.addAction("Pause")
			pauseAction.triggered.connect(self.pauseDownloadSelected)
			
			resumeAction = menu.addAction("Resume")
			resumeAction.triggered.connect(self.resumeDownloadSelected)
			
			menu.exec_(event.globalPos())
	
	def removeDownloadSelected(self, e):
		if self.selected_download:
			self.controller.removeDownload(self.selected_download)
	
	def pauseDownloadSelected(self, e):
		if self.selected_download:
			self.controller.pauseDownload(self.selected_download)
	
	def resumeDownloadSelected(self, e):
		if self.selected_download:
			self.controller.resumeDownload(self.selected_download)
	
	def rowOfDownload(self, download):
		for i, job in enumerate(self.jobs):
			if job == download:
				return i
		return -1
	
	def addDownload(self, download):
		item = QTreeWidgetItem(self)
		
		item.setText(0, "-")
		item.setText(1, "-")
		item.setText(2, "-")
		item.setText(3, "-")
		item.setText(4, "-")
		
		item.setTextAlignment(1, Qt.AlignHCenter)
		
		download.progressed.connect(self.updateDownload)
		
		self.jobs.append(download)
		
		#self.show()

	def updateDownload(self):
		download = self.sender()
		row = self.rowOfDownload(download)
		if row < 0:
			print("updateDownload: row not found for ", download.name())
			#self.addDownload(download)
			return
		
		item = self.topLevelItem(row)
		for col, func in enumerate(self.header_funcs):
			item.setText(col, func(download))
	
	def removeDownload(self, download):
		row = self.rowOfDownload(download)
		item = self.takeTopLevelItem(row)
		self.removeItemWidget(item, row)
		del self.jobs[row]

	def dragMoveEvent(self, event):
		url = QUrl(event.mimeData().text())
		if url.scheme() == "file" and url.path().endsWith(".torrent"):
			event.acceptProposedAction()

	def dropEvent(self, event):
		url = QUrl(event.mimeData().text())
		path = url.path()
		if QFile.exists(path) and path.toLower().endsWith(".torrent"):
			self.controller.addTorrentFile(str(path))
