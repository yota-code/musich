#!/usr/bin/env python3

import os
import socket

import cherrypy

from cc_pathlib import Path

import musich.catalog

musich_root_dir = Path(os.environ["MUSICH_root_DIR"])

musich_catalog_dir = Path(os.environ["MUSICH_catalog_DIR"])
musich_static_dir = Path(os.environ["MUSICH_static_DIR"])

class MusichRemote():

	catalog_pth = musich_catalog_dir / ".database/list.tsv.br"

	def __init__(self, is_ssl=False) :
		self.is_ssl = is_ssl

		self.catalog = musich.catalog.MusichCatalog(musich_catalog_dir)	

	@cherrypy.expose
	def get_track(self, * pos, ** nam) :
		if 'u' in nam :
			pth = musich_catalog_dir / nam['u']
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
		return (musich_static_dir / "html/index.html").read_bytes()

	@cherrypy.expose
	def get_meta(self, * pos, ** nam) :
		if is_ssl :
			return self.catalog.meta_pth.or_archive
		else :
			return self.catalog.meta_pth


if __name__ == '__main__' :

	cherrypy.config.update({
		'server.socket_host': socket.getfqdn(),
		'server.socket_port': 45080,
	}) # global config
		
	musich_config = {
		'/': {
			'tools.staticdir.root': str(musich_root_dir),
		},
		'/_static' : {
			'tools.staticdir.on': True,
			'tools.staticdir.dir': "static",
		}
	}

	cherrypy.tree.mount(MusichRemote(), '/', config=musich_config)

	cherrypy.engine.start()
	cherrypy.engine.block()
