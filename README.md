A simple web browser that allows to show websites (of course)
and downloads content from torrents when clicking on magnet links.

This browser supports links into torrent content: `<a href="magnet:?xt=hash/foo/index.html">Click here</a>`  
A magnet link / torrent files content can be browsed and displayed like a website.
New torrents can be created via drag&drop and then shared via magnet link.

This is an experiment to explore how web sites and P2P technology can be merged.

* OS supported: GNU/Linux
 * Ubuntu/Debian: `apt-get install python-libtorrent python-qt4`
* Dependencies: Python, libtorrent+python-bindings, PyQt/Webkit
* Current status: alpha
* License: GPLv3

Future plans:
 * less bugs :-)
 * mutable / signed content
 * access to the DHT as DNS addition
 * everything as browser plugin for Firefox/Chrome etc.

