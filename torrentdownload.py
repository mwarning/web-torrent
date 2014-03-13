import os
import sys
import math
import time

import libtorrent

from PyQt4.QtCore import *


class TorrentDownload(QObject):
	
	progressed = pyqtSignal()
	
	def __init__(self, handle, controller, storage_path):
		super(TorrentDownload, self).__init__()

		self.handle = handle
		self.controller = controller
		self.storage_path = storage_path #path to the content on disk

	#name stored in the torrent
	#not file/folder to be downloaded
	#not name of the torrent file
	def name(self):
		if self.handle.has_metadata():
			return self.handle.get_torrent_info().name()[:40]
		else:
			return '-'

	def pause(self):
		print("pause")
		self.handle.pause()

	def resume(self):
		self.handle.resume()

	def remove(self):
		self.controller.removeDownload(self)

	def reannounce(self):
		self.handle.force_reannounce()

	def recheck(self):
		self.handle.force_recheck()

	def file_priorities(self):
		return self.handle.file_priorities()

	def prioritize_files(self, priorities):
		self.handle.prioritize_files(priorities)

	'''
	0 piece is not downloaded at all
	1 normal priority. Download order is dependent on availability
	2 higher than normal priority. Pieces are preferred over pieces with the same availability, but not over pieces with lower availability
	3 pieces are as likely to be picked as partial pieces.
	4 pieces are preferred over partial pieces, but not over pieces with lower availability
	5 currently the same as 4
	6 piece is as likely to be picked as any piece with availability 1
	7 maximum priority, availability is disregarded, the piece is preferred over any other piece with lower priority
	'''

	def set_file_priority(self, index, priority):
		self.handle.file_priority(index, priority)

	def file_priority(self, index):
		return self.handle.file_priority(index)

	def set_priority(self, priority):
		self.handle.set_priority(priority)

	def status(self):
		s = self.handle.status()
		return "{}".format(s.state)

	def progress(self):
		s = self.handle.status()
		return int(s.progress * 100)

	def num_peers(self):
		s = self.handle.status()
		return s.num_peers

	def num_seeds(self):
		s = self.handle.status()
		return s.num_seeds

	def num_files(self):
		return self.handle.torrent_file().num_files()

	def has_metadata(self):
		return self.handle.has_metadata()

	def total_size(self):
		return self.handle.get_torrent_info().total_size()

	#returns list of file sizes
	def file_progress(self):
		return self.handle.file_progress()

	def download_rate(self):
		s = self.handle.status()
		return s.download_rate / 1000

	def upload_rate(self):
		s = self.handle.status()
		return s.upload_rate / 1000

	def info_hash(self):
		s = self.handle.status()
		return str(s.info_hash).lower()

	def files(self):
		f = self.handle.torrent_file()
		return f.files()

	'''
	Select a single file or folder for download
	'''
	def select_file(self, path):
		priorities = self.handle.file_priorities()
		files = self.handle.torrent_file().files()
		now = time.clock()

		if path[0] == "/":
			path = path[1:]

		def schedule_file(i):
			if priorities[i] == 0:
				self.set_file_priority(i, 1)

		if len(path) == 0 or path == "/":
			self.resume()
			for i in range(0, len(files)):
				schedule_file(i)
			return

		for i, file in enumerate(files):
			if file.path == path:
				schedule_file(i)
				return

			#if path.startwith(path):
			#	schedule_file(i)

	def contains_file(self, path):
		if len(path) == 0 or path[-1] == "/":
			return False
		
		if path[0] == "/":
			path = path[1:]
		
		for file in self.files():
			if file.path == path:
				return True
		return False