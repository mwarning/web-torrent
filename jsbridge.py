
from PyQt4.QtCore import *


class JavaScriptBridge(QObject):
	bar = pyqtSignal()
	
	def __init__(self, controller, webview = None):
		super(JavaScriptBridge, self).__init__()
		
		self.controller = controller
		self.webview = webview
		self.last_dropped_urls = []

	@pyqtSlot(QString, result="QString")
	def getFullPath(self, file_name):
		for url in self.last_dropped_urls:
			if url.path().split('/')[-1] == file_name:
				return url.path()
		
		return QString("")
	
	@pyqtSlot(QString, QString)
	def torrentAction(self, action, info_hash):
		d = self.controller.findTorrentByHash(str(info_hash))
		if d:
			if action == "remove":
				d.remove()
			elif action == "resume":
				d.resume()
			elif action == "pause":
				d.pause()
			else:
				print("Unknown action: {}".format(action))
		else:
			print("Download not found: {}".format(info_hash))
			
	
	@pyqtSlot(result="QString")
	def getAllTorrents(self):
		out = []
		
		out.append(u'{"torrents" : [')
		for i, d in enumerate(self.controller.downloads):
			#
			
			if i != 0:
				out.append(u',')
			
			out.append(u'{')
			out.append(u'"hash":"{}",'.format(d.info_hash()))
			out.append(u'"name":"{}",'.format(d.name()))
			out.append(u'"progress":{},'.format(d.progress()))
			out.append(u'"num_peers":{},'.format(d.num_peers()))
			out.append(u'"num_seeds":{},'.format(d.num_seeds()))
			out.append(u'"status":"{}",'.format(d.status()))
			if d.has_metadata():
				out.append(u'"total_size":"{}",'.format(d.total_size()))
				out.append(u'"num_files":"{}",'.format(d.num_files()))
			
			out.append(u'"upload_rate":{},'.format(d.upload_rate()))
			out.append(u'"download_rate":{}'.format(d.download_rate()))
			out.append(u'}')
		out.append(u']}')
		
		return QString(u''.join(out))
	
	@pyqtSlot(QString, QString, result="QString")
	def getTorrentFiles(self, info_hash, abs_base_path):
		out = []
		print("getTorrentFiles: path {}".format(abs_base_path))
		
		out.append(u'{"torrent_files" : [')
		
		if len(abs_base_path) == 0:
			abs_base_path = "/"
		if abs_base_path[-1] != "/":
			abs_base_path += "/"
		if abs_base_path[0] != '/':
			abs_base_path = "/"+ abs_base_path
		
		subfolders = {}
		
		d = self.controller.findTorrentByHash(info_hash)
		if d and d.has_metadata():
			files = d.files()
			priorities = d.file_priorities()
			progress = d.file_progress()
			
			if len(files) != len(priorities) or len(files) != len(progress):
				print("Element mismatch")
				return
			
			first = True
			for i, file in enumerate(files):
				if file.pad_file:
					continue
				
				abs_file_path = file.path
				if len(abs_file_path) == 0 or abs_file_path[0] != '/':
					abs_file_path = "/"+ abs_file_path
				
				if not abs_file_path.startswith(abs_base_path):
					continue
				
				rel_file_path = abs_file_path[len(abs_base_path):]
				
				pos = rel_file_path.find("/")
				if pos < 0:
					#file in current path
					file_name = rel_file_path
					
					if first:
						first = False
					else:
						out.append(u',')
					
					out.append(u'{')
					out.append(u'"name":"{}",'.format(file_name))
					out.append(u'"path":"{}",'.format(file.path))
					out.append(u'"size":"{}",'.format(file.size))
					out.append(u'"priority":"{}",'.format(priorities[i]))
					out.append(u'"progress":"{}"'.format(progress[i]))
					out.append(u'}')
				else:
					#file in subfolder
					folder_name = rel_file_path[0:pos]
					
					if folder_name in subfolders:
						folder = subfolders[folder_name]
						folder["size"] += file.size
						folder["priority"].append(priorities[i])
						folder["progress"].append(progress[i])
					else:
						folder = {}
						subfolders[folder_name] = folder
						folder["size"] = 0
						folder["priority"] = []
						folder["progress"] = []
			
			for folder_name, folder in subfolders.iteritems():
				if first:
					first = False
				else:
					out.append(u',')
				
				out.append(u'{')
				out.append(u'"name":"{}",'.format(folder_name))
				out.append(u'"size":"{}",'.format(folder["size"]))
				out.append(u'"priority":"{}",'.format(0))
				out.append(u'"progress":"{}"'.format(0))
				out.append(u'}')
		
		
		out.append(u']}')
		print(u''.join(out))
		return QString(u''.join(out))
	
	@pyqtSlot(int, result="QString")
	def getFolderSize(start_path):
		#some security
		if self.getFullPath(start_path).length() == 0:
			return -1
		
		total_size = 0
		for dirpath, dirnames, filenames in os.walk(start_path):
			for f in filenames:
				fp = os.path.join(dirpath, f)
				total_size += os.path.getsize(fp)
		
		return total_size
	
	@pyqtSlot(int, result="QString")
	def getFolderCount(start_path):
		#some security
		if self.getFullPath(start_path).length() == 0:
			return -1
		
		total_count = 0
		for dirpath, dirnames, filenames in os.walk(start_path):
			for f in filenames:
				total_count += 1
		
		return total_count
	
	def setProgress(self, progress):
		frame = self.webview.page().mainFrame()
		frame.evaluateJavaScript('setProgress({})'.format(progress))
	
	@pyqtSlot(QStringList, result="QString")
	def createTorrent(self, paths):
		paths = [str(p) for p in paths]
		
		torrent_file = os.path.abspath("a_new.torrent")
		TorrentController.createTorrent(paths, torrent_file, self.setProgress)
		
		return torrent_file
