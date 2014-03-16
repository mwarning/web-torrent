import os
import sys
import math
import json

import libtorrent

from PyQt4.QtCore import *

from torrentdownload import TorrentDownload


def formatSize(val):
	prefix = ['B', 'kB', 'MB', 'GB', 'TB']
	for i in range(len(prefix)):
		if math.fabs(val) < 1000:
			return '{}{}'.format(val, prefix[i])
		val /= 1000

	return '{}{}'.format(val, "PB")

def formatSpeed(val):
	return formatSize(val) +"/s"

#prevent cross side attacks
#convert to html unicode 
def formatText(text):
	s = []
	for c in text:
		n = ord(c)
		if n < 32 or n > 126 or "<>[](){}".find(c) > -1:
			s.append( "&#"+str(n))
		else:
			s.append(c)
	return "".join(s)


#find the first single '/'
def findSingleSlash(href):
	offset = 0
	pos = 0
	while True:
		pos = href.find('/', offset)
		if pos < 0:
			return len(href)

		if (pos+1) < len(href) and href[pos+1] == '/':
			pos = pos + 2
			while (pos+1) < len(href) and href[pos+1] == '/':
				pos = pos + 2
			offset = pos
		else:
			return pos

class TorrentController(QObject):
	'''send console input and output'''
	download_added = pyqtSignal(TorrentDownload)
	download_removed = pyqtSignal(TorrentDownload)

	def __init__(self, cache_path):
		super(TorrentController, self).__init__()

		settings = libtorrent.session_settings()
		settings.user_agent = 'torrent_browser/' + libtorrent.version
		settings.use_dht_as_fallback = False
		settings.volatile_read_cache = False

		ses = libtorrent.session()
		ses.set_download_rate_limit(0)
		ses.set_upload_rate_limit(0)
		ses.listen_on(6881, 6891)
		ses.set_alert_mask(0xfffffff)
		ses.set_settings(settings)

		#start local source discovery
		ses.start_lsd()

		#start distributed hash table
		ses.start_dht()

		#start router port forwarding
		ses.start_upnp()
		ses.start_natpmp()

		#add bootstrapping nodes
		ses.add_dht_router("router.bittorrent.com", 6881)
		ses.add_dht_router("router.utorrent.com", 6881)
		ses.add_dht_router("router.bitcomet.com", 6881)
		
		self.session = ses
		self.downloads = list()
		self.alive = True

		self.cache_path =  cache_path
		print("(I) Cache directory: {}".format(cache_path))

		if not os.path.exists(self.cache_path):
			os.makedirs(self.cache_path)

		self.timer = QTimer()
		self.timer.timeout.connect(self.sendUpdates)
		self.timer.start(500)

	def loadSettings(self, path):
		if not os.path.exists(path):
			return

		text = open(path, 'rb').read()
		obj = json.loads(text)
		settings = libtorrent.session_settings()

		settings.set_download_rate_limit(int(obj.get('download_rate_limit', 0)))
		settings.set_upload_rate_limit(int(obj.get('upload_rate_limit', 0)))

		libtorrent.session().set_settings(settings)

	def storeSettings(self, path):
		obj = {}
		settings = libtorrent.session_settings()

		obj['download_rate_limit'] = int(settings.download_rate_limit)
		obj['upload_rate_limit'] = int(settings.upload_rate_limit)

		data = json.dumps(obj)
		file = open(path,'wb')
		file.write(data)
		file.close()

	def sendUpdates(self):
		for download in self.downloads:
			download.progressed.emit()

	def createTorrent(self, torrent_file_path, content_folder_path, progress_cb):
		TorrentController.createTorrent(torrent_file_path, content_folder_path, progress_cb)

	def addTorrentFile(self, file_path, paused = False):
		if not os.path.isfile(file_path):
			print("File does not exist: {}".format(file_path))
			return None
		
		info = libtorrent.torrent_info(file_path)
		info_hash = str(info.info_hash()).lower()
		
		download = self.findTorrentByHash(info_hash)
		if download:
			return download
		else:
			save_path = self.cache_path
			
			atp = {}
			atp['ti'] = info
			atp["save_path"] = save_path
			if paused:
				atp['flags'] = libtorrent.add_torrent_params_flags_t.flag_paused
			else:
				atp['flags'] = 0
			
			try:
				atp["resume_data"] = open(file_path + '.fastresume', 'rb').read()
			except:
				pass

			handle = self.session.add_torrent(atp)
			handle.set_max_connections(60)
			handle.set_max_uploads(-1)
			
			download = TorrentDownload(handle, self, save_path)
			self.downloads.append(download)
			self.download_added.emit(download)
			
			return download
	
	def addMagnetLink(self, url, paused = False):
		params = libtorrent.parse_magnet_uri(url)
		info_hash = str(params['info_hash']).lower()

		download = self.findTorrentByHash(info_hash)
		if download:
			return download
		else:
			save_path = self.cache_path

			atp = {}
			atp["save_path"] = save_path
			atp["storage_mode"] = libtorrent.storage_mode_t.storage_mode_sparse
			atp["auto_managed"] = True
			atp["duplicate_is_error"] = True
			#atp["paused"] = paused
			atp["url"] = url
			if paused:
				atp['flags'] = libtorrent.add_torrent_params_flags_t.flag_paused
			else:
				atp['flags'] = 0

			handle = self.session.add_torrent(atp)
			handle.set_max_connections(60)
			handle.set_max_uploads(-1)

			download = TorrentDownload(handle, self, save_path)
			self.downloads.append(download)
			self.download_added.emit(download)
			return download

	def settings(self):
		return libtorrent.session_settings()

	def findTorrentByHash(self, hash):
		for download in self.downloads:
			if download.info_hash() == hash:
				return download
		return None

	@staticmethod
	def createTorrent(torrent_file_path, content_folder_path, progress_cb = None):
		print("createTorrent")

		fs = libtorrent.file_storage()

		if not os.path.isabs(torrent_file_path):
			raise "Torrent path not absolute"

		if not os.path.isabs(content_folder_path):
			raise "Content path not absolute"

		libtorrent.add_files(fs, content_folder_path)

		if fs.num_files() == 0:
			print("No files to add.")
			return

		t = libtorrent.create_torrent(fs, piece_size=0, pad_file_limit=(4 * 1024 * 1024))

		def progress(piece_num):
			if progress_cb:
				pc = int((100.0 * (1.0+ piece_num)) / fs.num_pieces())
				progress_cb(pc)
		
		parent = os.path.dirname(content_folder_path)
		libtorrent.set_piece_hashes(t, parent, progress)

		data = libtorrent.bencode(t.generate())

		file = open(torrent_file_path,'wb')
		file.write(data)
		file.close()

	#TODO: remove and use html interface
	def dumpTorrent(self, torrent_file):
		size = os.path.getsize(torrent_file)
		if size < 0 or size > (40 * 1000000):
			return 'error'

		t = libtorrent.torrent_info(torrent_file)

		site = []
		site.append('File: {}'.format(torrent_file))

		nodes = t.nodes()
		if nodes:
			site.append('Nodes:')
			for node in nodes:
				site.append(" - "+formatText(node))

		trackers = t.trackers()
		if trackers:
			site.append('Trackers:')
			for tracker in trackers:
				site.append(" - "+formatText(tracker))

		magnet_uri = libtorrent.make_magnet_uri(t)

		site.append('name: {}'.format(formatText(t.name())))
		site.append('num_files: {}'.format(t.num_files()))
		site.append('info_hash: {}'.format(t.info_hash()))
		site.append('num_pieces: {}'.format(t.num_pieces()))
		site.append('piece_length: {}'.format(t.piece_length()))
		site.append('magnet_uri: {}'.format(magnet_uri))

		comment = t.comment()
		if comment:
			site.append('comment: {}'.format(formatText(comment)))

		creator = t.creator()
		if creator:
			site.append('creator: {}'.format(formatText(creator)))

		fs = t.files()

		site.append('Files:')
		for f in fs:
			site.append(' - {} ({})</li>'.format(path, formatSize(f.size)))

		return '\n'.join(site)

	def foundAddresses(self, addrs):
		print("foundAddresses: {}".format(addrs))

	def dht_lookup(self, hash, announce=False):
		print("lookupHash {}".format(hash))
		self.session.dht_announce("abcdefg", 1234, announce, self.foundAddresses)

	def removeDownload(self, download):
		print("Controler.removeDownload")
		for i, d in enumerate(self.downloads):
			if d == download:
				print("Found download")
				del self.downloads[i]
				self.download_removed.emit(download)
				self.session.remove_torrent(download.handle, libtorrent.options_t.delete_files)
				
				path = os.path.join(self.cache_path, d.info_hash())
				os.remove(path+'.torrent')
				os.remove(path+'.torrent.fastresume')
				
				break

	def setLSD(self, enable):
		pass

	def getLSD(self):
		return True

	def setDHT(self, enable):
		pass

	def getDHT(self):
		return True

	def shutdown(self):
		print("TorrentController.shutdown")

		self.session.pause()

		for d in self.downloads:
			h = d.handle
			if h.is_valid() and h.has_metadata():
				file = os.path.join(self.cache_path, d.info_hash())

				data = libtorrent.bdecode(h.get_torrent_info().metadata())
				data = libtorrent.bencode({ "info" : data })
				open(file+'.torrent', 'wb').write(data)

				data = h.write_resume_data()
				data = libtorrent.bencode(data)
				open(file + '.torrent.fastresume' , 'wb').write(data)

		print("done")
