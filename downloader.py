
from PyQt4 import QtCore, QtGui, QtNetwork, QtWebKit


class Downloader(QtCore.QObject):

	def __init__(self, parentWidget, manager):
		super(Downloader, self).__init__(parentWidget)

		self.manager = manager
		self.reply = None
		self.downloads = {}
		self.path = ""
		self.parentWidget = parentWidget

	def chooseSaveFile(self, url):
		fileName = url.path().split("/")[-1]
		if len(self.path) != 0:
			fileName = QDir(path).filePath(fileName)

		return QtGui.QFileDialog.getSaveFileName(self.parentWidget, u"Save File", fileName);

	def startDownload(self, request):
		self.downloads[request.url().toString()] = self.chooseSaveFile(request.url())

		reply = self.manager.get(request)
		reply.finished.connect(self.finishDownload)

	def saveFile(self, reply):
		newPath = self.downloads.get(reply.url().toString())

		if not newPath:
			newPath = self.chooseSaveFile(reply.url())

		if len(newPath) != 0:
			file = QtCore.QFile(newPath)
			if file.open(QtCore.QIODevice.WriteOnly):
				file.write(reply.readAll())
				file.close()
				path = QtCore.QDir(newPath).dirName()
				QtGui.QMessageBox.information(self.parentWidget, u"Download Completed", u"Saved '%s'." % newPath)
			else:
				QtGui.QMessageBox.warning(self.parentWidget, u"Download Failed", u"Failed to save the file.")

	def finishDownload(self):
		reply = self.sender()
		self.saveFile(reply)
		self.downloads.pop(reply.url().toString(), None)
		reply.deleteLater()
