#!/usr/bin/env python

import os
import sys
import math
import time
import signal
import urllib2
import subprocess
from jsbridge import JavaScriptBridge

from dhtview import DhtView
from torrentview import TorrentView
from torrentcontroller import TorrentController, formatSize, formatText, findSingleSlash
from torrentdownload import TorrentDownload

from downloader import Downloader

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
from PyQt4.QtNetwork import *


class NetworkAccessManager(QNetworkAccessManager):

	def __init__(self, manager, parent):
		super(NetworkAccessManager, self).__init__(parent)

		self.setCache(manager.cache())
		self.setCookieJar(manager.cookieJar())
		self.setProxy(manager.proxy())
		self.setProxyFactory(manager.proxyFactory())

	def createRequest(self, operation, request, device):
		url = request.url()

		if operation == QNetworkAccessManager.GetOperation:
			pass

		return QNetworkAccessManager.createRequest(self, operation, request, device)


class WebView(QWebView):
	tabOpenRequested = pyqtSignal(QUrl)

	def __init__(self, parent = None):
		super(WebView, self).__init__(parent)

		oldManager = self.page().networkAccessManager()
		newManager = NetworkAccessManager(oldManager, self)
		self.page().setNetworkAccessManager(newManager)

		self.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
		self.page().setForwardUnsupportedContent(True)
		self.lastClickedMouseButton = Qt.LeftButton

		self.downloader = Downloader(self, newManager)
		self.page().unsupportedContent.connect(self.downloader.saveFile)
		self.page().downloadRequested.connect(self.downloader.startDownload)

		self.linkClicked.connect(self.loadContent)

		self.jsbridge = None
		self.page().mainFrame().javaScriptWindowObjectCleared.connect(self.addJSObject)

	def addJSObject(self):
		''' Only allow access JavaScriptBridge from local files'''
		if self.url().scheme() == "file" and self.url().path().endsWith(".html"):
			self.jsbridge = JavaScriptBridge(controller, self)
			self.page().mainFrame().addToJavaScriptWindowObject("jsbridge", self.jsbridge);
		else:
			self.jsbridge = None

	def dragMoveEvent(self, event):
		print("WebView.dragMoveEvent")
		urls = event.mimeData().urls()

		if self.jsbridge:
			event.acceptProposedAction()
		elif len(urls) == 1:
			url = urls[0]
			path = urls[0].path()
			event.acceptProposedAction()
		
		QWebView.dragMoveEvent(self, event)

	def dropEvent(self, event):
		print("WebView.dropEvent")

		urls = event.mimeData().urls()

		if self.jsbridge:
			self.jsbridge.last_dropped_urls = urls

		if len(urls) == 1:
			url = urls[0]
			path = str(urls[0].path())

			if url.scheme() == "magnet":
				#todo
				print("self.addMagnetLink(str(url.toString()))")
			elif url.scheme() == "file" and os.path.isfile(path) and path.endswith(".torrent"):
				self.handleUrl(url)

		QWebView.dropEvent(self, event)

	def handleUrl(self, url):
		print("handleUrl: {}".format(url))

		href = str(url.toString())
		pos = findSingleSlash(href)
		base_url = href[:pos]
		relative_path = href[pos+1:]

		d = None
		if url.scheme() == "magnet" or url.path().endsWith(".torrent"):
			if url.scheme() == "magnet":
				d = controller.addMagnetLink(base_url)
			else:
				d = controller.addTorrentFile(base_url)

			if not d:
				path = os.path.abspath("ui/error.html")
			elif not d.has_metadata():
				path =  os.path.abspath("ui/error.html")
			elif len(relative_path) == 0:
				path = os.path.abspath("ui/torrent_viewer.html")
				path += "?hash=" + d.info_hash()
			elif d.contains_file(relative_path):

				#select for download if file is not yet downloaded
				d.select_file(relative_path)

				path = os.path.join(d.storage_path, relative_path)
			else:
				path = os.path.abspath("ui/torrent_viewer.html")
				path += "?hash=" + d.info_hash() + "&path=" + relative_path

			self.load(QUrl("file://"+path))
		elif url.scheme() == "file":
			if len(relative_path) > 0 and relative_path[-1] == '/':
				path = os.path.abspath("ui/folder_viewer.html")
				path += "?path=" + relative_path
				self.load(QUrl("file://"+path))
			else:
				self.load(url)
		elif url.scheme() == "https" or url.scheme() == "http":
			self.load(url)
		else:
			path = os.path.abspath("ui/error.html")
			self.load(QUrl("file://"+path))

	def loadContent(self, url):
		print("loadContent: {}".format(url.toString()))
		
		if self.lastClickedMouseButton == Qt.LeftButton:
			self.handleUrl(url)
		elif self.lastClickedMouseButton == Qt.MidButton:
			self.tabOpenRequested.emit(url)
		elif self.lastClickedMouseButton == Qt.RightButton:
			pass
	

class TabWidget(QWidget):
	
	def __init__(self, parent):
		super(TabWidget, self).__init__(parent)
		
		self.addressBar = QLineEdit(self)
		self.addressBar.setSizePolicy(QSizePolicy.Expanding, self.addressBar.sizePolicy().verticalPolicy())
		self.web = WebView(self)
		self.infoLabel = QLabel()
		
		toolBar = QToolBar("Navigation")
		toolBar.addAction(self.web.pageAction(QWebPage.Back))
		toolBar.addAction(self.web.pageAction(QWebPage.Forward))
		toolBar.addAction(self.web.pageAction(QWebPage.Reload))
		toolBar.addAction(self.web.pageAction(QWebPage.Stop))
		toolBar.addWidget(self.addressBar)
		
		vlayout = QVBoxLayout(self)
		vlayout.addWidget(toolBar)
		vlayout.addWidget(self.web)
		vlayout.addWidget(self.infoLabel)

		self.addressBar.returnPressed.connect(self.addressBarReturnPressed)

		self.web.urlChanged.connect(self.webUrlChanged)
		self.web.loadFinished.connect(self.webLoadFinished)

		self.web.page().linkHovered.connect(self.onLinkHovered)

		QWebSecurityOrigin.addLocalScheme("magnet")
		QNetworkProxyFactory.setUseSystemConfiguration(True)

	def onLinkHovered(self, link, title, textContent):
		if len(link) > 80:
			self.infoLabel.setText(link[:80]+"...")
		else:
			self.infoLabel.setText(link)

	def webLoadFinished(self, ok):
		pass

	def webUrlChanged(self, url):
		print("setAddressBar")
		self.addressBar.setText(url.toString())

	def addressBarReturnPressed(self):
		print("loadAddressBar")
		text = self.addressBar.text()
		url = QUrl.fromEncoded(text.toUtf8(), QUrl.TolerantMode)
		self.web.loadContent(url)

class MainWindow(QMainWindow):
	def __init__(self, controller, parent=None):
		super(MainWindow, self).__init__(parent)

		self.setWindowTitle("Browser")
		self.tabWidget = QTabWidget(self)
		self.tabWidget.setTabsClosable(False)
		self.tabWidget.setMovable(True)
		self.tabWidget.setUsesScrollButtons(True)

		self.controller = controller

		self.tabWidget.tabCloseRequested.connect(self.closeTab)
		self.tabWidget.currentChanged.connect(self.currentChanged)

		self.setCentralWidget(self.tabWidget)		
		self.setUnifiedTitleAndToolBarOnMac(True)

		self.setupMenu()

	def setupMenu(self):
		self.showDownloadsAction = QAction("Show &Torrents", self);
		self.showDhtAction = QAction("Show &DHT", self);
		self.showCreatorAction = QAction("Create Torrent", self);
		self.showSourceAction = QAction("Show Source", self);
		self.showSourceAction.triggered.connect(self.showSource)

		fileMenu = self.menuBar().addMenu("&File")
		fileMenu.addAction(self.showDownloadsAction)
		fileMenu.addAction(self.showDhtAction)
		fileMenu.addAction(self.showCreatorAction)
		fileMenu.addAction(self.showSourceAction)
		fileMenu.addSeparator()
		fileMenu.addAction("E&xit", self.close)

		lsdAction = QAction("Local Source Discovery (LSD)", self);
		lsdAction.setCheckable(True)
		lsdAction.setChecked(self.controller.getLSD())
		lsdAction.triggered.connect(self.controller.setLSD)

		dhtAction = QAction("Distributed Hash Table (DHT)", self);
		dhtAction.setCheckable(True)
		dhtAction.setChecked(self.controller.getDHT())
		dhtAction.triggered.connect(self.controller.setDHT)

		libtMenu = self.menuBar().addMenu("&libtorrent")
		libtMenu.addAction(lsdAction)
		libtMenu.addAction(dhtAction)

	def keyPressEvent(self, event):
		if (event.modifiers() & Qt.ControlModifier) and (event.key() == Qt.Key_T):
			if self.tabWidget.count() < 15:
				self.openTab(QUrl("http://google.com"))
			else:
				print("Too many tabs open.")
				event.ignore()
		else:
			event.ignore()

	def showSource(self):
		tab = self.tabWidget.currentWidget()
		if tab:
			self.textEdit = QTextEdit()
			self.textEdit.setPlainText(tab.web.page().currentFrame().toHtml())
			self.textEdit.show()

	def closeEvent(self, event):
		torrent_view.close()
		dht_view.close()
		event.accept()

	def closeTab(self, index):
		if self.tabWidget.count() == 2:
			self.tabWidget.setTabsClosable(False)

		self.tabWidget.removeTab(index)
	
	def openTab(self, url):
		tab = TabWidget(self)

		tab.web.loadFinished.connect(self.loadFinished)
		tab.web.tabOpenRequested.connect(self.openTab)
		tab.web.loadContent(url)

		self.tabWidget.addTab(tab, 'loading...')

		if self.tabWidget.count() == 2:
			self.tabWidget.setTabsClosable(True)

	def currentChanged(self, index):
		tab = self.tabWidget.widget(index)
		if tab:
			self.setWindowTitle(tab.web.title())
		else:
			self.setWindowTitle("-")
	
	def loadFinished(self, url):
		print("loadFinished")
		tab = self.sender().parent()
		index = self.tabWidget.indexOf(tab)
		self.tabWidget.setTabText(index, tab.web.title())
		#self.setWindowTitle(tab.web.title())

def autoCreateTorrents(controller, content_folders_path):
	print("(I) Create Torrents files.")
	
	for name in os.listdir(content_folders_path):
		path = os.path.join(content_folders_path, name)
		if os.path.isfile(path):
			continue
		
		torrent_file_path = path +".torrent"
		content_folder_path = path
		
		if os.path.exists(torrent_file_path):
			continue
		
		def progress_cb(p):
			sys.stdout.write("\r{} - {}%".format(os.path.basename(torrent_file_path), p))
			if p == 100:
				sys.stdout.write("\n")
		
		controller.createTorrent(torrent_file_path, content_folder_path, progress_cb)

def autoAddTorrents(controller, content_folders_path):
	print("(I) Add Torrent files.")
	content_folders_path = os.path.abspath(content_folders_path)
	
	for name in os.listdir(content_folders_path):
		path = os.path.join(content_folders_path, name)
		if os.path.isfile(path) and path.endswith(".torrent"):
			print("(I) Add {}".format(path))
			controller.addTorrentFile(path)

if __name__ == "__main__":
	app = QApplication([])

	cache_path = os.path.abspath("cache/")

	controller = TorrentController(cache_path)
	main_window = MainWindow(controller)
	torrent_view = TorrentView(controller)
	dht_view = DhtView(controller)

	main_window.showDhtAction.triggered.connect(dht_view.show)
	main_window.showDownloadsAction.triggered.connect(torrent_view.show)

	#autoCreateTorrents(controller, cache_path)
	autoAddTorrents(controller, cache_path)

	'''handler for the SIGINT signal'''
	def sigint_handler(*args):
		print("sigint_handler")
		QApplication.quit()

	signal.signal(signal.SIGINT, sigint_handler)

	def aboutToQuit():
		print("aboutToQuit")
		controller.shutdown()
		time.sleep(1)

	qApp.aboutToQuit.connect(aboutToQuit)

	main_window.openTab(QUrl("file://" + os.path.abspath("ui/torrents_viewer.html")))
	main_window.openTab(QUrl("file://" + os.path.abspath("ui/torrent_builder.html")))
	main_window.openTab(QUrl("file://" + os.path.abspath("cache/some_local_content/index.html")))
	main_window.show()

	sys.exit(app.exec_())
	