#!/usr/bin/env python3

import os

import cherrypy

from cc_pathlib import Path

import musich.scan

musich_root_dir = Path(os.environ["MUSICH_root_DIR"])
musich_catalog_dir = Path(os.environ["MUSICH_catalog_DIR"])
musich_static_dir = Path(os.environ["MUSICH_static_DIR"])

class MusishServer():

	catalog_pth = musich_catalog_dir / ".database/list.tsv.br"

	def __init__(self) :
	
		if not self.catalog_pth.is_file() :
			u = musich.scan.MusicDatabase(self.catalog_pth.parent)	

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
	def get_list(self, * pos, ** nam) :
		return self.catalog_pth.read_bytes()




