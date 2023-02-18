#!/usr/bin/env python3

import time

import cherrypy

from cc_pathlib import Path

class MusichLocal() :
	def __init__(self, static_dir, m_queue, m_catalog, m_player) :
		# Gst.init(None)

		self.static_dir = static_dir

		self.m_queue = m_queue
		self.m_catalog = m_catalog
		self.m_player = m_player

	@cherrypy.expose
	def index(self) :
		return (self.static_dir / 'html' / 'local.html').read_text()

	@cherrypy.expose
	def _get_meta(self, * pos, ** nam) :
		cherrypy.response.headers['Content-Type'] = 'text/javascript'
		return (self.m_catalog.c_dir / ".database" / "meta.json").read_bytes()

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def _get_info(self, * pos, ** nam) :
		v_map = {k: int(nam.get(k, -1)) for k in "pn"}
		return self.info(** v_map)

	def info(self, p=-1, n=-1) :

		r_map = dict()
		if p is not None and p != self.m_queue.v_prev :
			r_map['prev'] = [self.m_queue.v_prev, self.m_queue.prev_lst]
		if n is not None and n != self.m_queue.v_next :
			r_map['next'] = [self.m_queue.v_next, self.m_queue.next_lst]

		r_map['track'] = [
			self.m_player.play_track, # hash of the loaded track
			self.m_player.get_position(), # current progress on the track (in ms)
			self.m_player.get_duration(), # duration of the loaded track (in ms)
			self.m_player.play_status # status of the play (None: STOPPED, False: PAUSED, True: PLAYING)
		]

		return r_map

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def _push_to_queue(self, * pos, ** nam) :
		print(f"MusichLocal._push_to_queue({pos}, {nam})")
		if 'h' in nam and nam['h'] in self.m_catalog.meta_map :
			if 'a' in nam :
				pass # add the whole album
			else :
				if 'f' in nam :
					self.m_queue.push_to_next(nam['h'])
				else :
					self.m_queue.push_to_end(nam['h'])

		return self.info(p=None)
	
	@cherrypy.expose
	@cherrypy.tools.json_out()
	def _pull_from_queue(self, * pos, ** nam) :
		print(f"MusichLocal._pull_from_queue({pos}, {nam})")
		if 'h' in nam and 'i' in nam :
			self.m_queue.pull(nam['h'], int(nam['i']))
		
		return self.info(p=None)

	def _about_to_finish(self, * pos, ** nam) :
		self._play()

	def _play(self, m_cur=None) :
		print(f"\x1b[35mMusichLocal._play(\x1b[36m{m_cur}\x1b[35m)\x1b[0m")
		if m_cur is None :
			try :
				m_cur = self.m_queue.que_lst.pop(0)
			except :
				pass
		self.m_cur = m_cur

		if self.m_cur is None :
			return

		self.m_hst.push(self.m_cur)

		if not self.m_queue :
			for pth in (self.m_catalog.c_dir / 'sample').glob('*.wav') :
				key = str(pth.relative_to(self.m_catalog.c_dir))
				if '4' in key or '5' in key :
					self.m_queue.append(key)

		m_pth = self.m_catalog.c_dir / self.m_cur

		print(f"MusichLocal._play_this({m_cur}) --> {self.m_cur}")
		
		self.g.set_state(Gst.State.NULL)
		self.g.set_property("uri", f"file://{m_pth}")
		self.g.set_state(Gst.State.PLAYING)

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def _set_position(self, * pos, ** nam) :
		if 't' in nam :
			self.m_player.set_position(int(nam['t']))
		return self.info(p=None, n=None)

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def _play_next(self, * pos, ** nam) :
		print(f"MusichLocal.play_next()")
		self.m_player.pop()
		return self.info()

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def _play_pause(self) :
		print(f"MusichLocal.play_pause()")
		return self.m_player.toggle()

	# @cherrypy.expose
	# @cherrypy.tools.json_out()
	# @cherrypy.tools.json_in()
	# def update_queue(self, * pos, ** nam) :
	# 	when, what = cherrypy.request.json
	# 	if when == "next" :
	# 		self.m_queue.add_next(what)
	# 	elif when == "after" :
	# 		self.m_queue.add_after(what)
	# 	elif when == "now" :
	# 		self._play(what)

	# 	print("\n\n>>> update_queue", pos, nam, cherrypy.request.json, "\n\n")
	# 	return {
	# 		"cur": self.m_cur,
	# 		"que": self.m_queue.que_lst,
	# 		"_play_": self.g.get_state(1000).state == Gst.State.PLAYING,
	# 	}
