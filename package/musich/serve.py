#!/usr/bin/env python3

"""

export MUSICH_root_DIR=/mnt/workbench/source/musich
export MUSICH_data_DIR=/mnt/workbench/source/musich/data
export MUSICH_static_DIR=/mnt/workbench/source/musich/static
export MUSICH_track_DIR=/media/yoochan/front/music/library

"""

import os

import cherrypy

from cc_pathlib import Path

track_dir = Path(os.environ["MUSICH_track_DIR"])
data_dir = Path(os.environ["MUSICH_data_DIR"])
static_dir = Path(os.environ["MUSICH_static_DIR"])
root_dir = Path(os.environ["MUSICH_root_DIR"])

class MusishServer():
	@cherrypy.expose
	def get_track(self, * pos, ** nam) :
		if 'u' in nam :
			pth = track_dir / nam['u']
			if not pth.is_file() :
				print(f"file not found : {pth}")
				raise cherrypy.HTTPError(404)
			if pth.suffix in ['.opus', '.ogg', '.spx'] :
				cherrypy.response.headers['Content-Type'] = 'audio/ogg'
			return pth.read_bytes()
		else :
			raise cherrypy.HTTPError(400)

	@cherrypy.expose
	def index(self, * pos, ** nam) :
		return (root_dir / "static/html/index.html").read_bytes()

	@cherrypy.expose
	def get_data(self, * pos, ** nam) :
		pth = data_dir / nam.get('d', '__local__.tsv')
		return pth.read_bytes()


cherrypy.config.update({
	# 'server.socket_host': '127.0.0.1',
	'server.socket_host': '192.168.1.104',
	'server.socket_port': 8080,
}) # global config
	
musich_config = {
	'/': {
		'tools.staticdir.root': str(root_dir),
	},
	'/_static' : {
		'tools.staticdir.on': True,
		'tools.staticdir.dir': "static",
	}
}


cherrypy.tree.mount(MusishServer(), '/', config=musich_config)

cherrypy.engine.start()
cherrypy.engine.block()
