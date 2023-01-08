#!/usr/bin/env python3

import collections
import datetime
import json
import os

import gi

gi.require_version('Gst', '1.0')

from gi.repository import Gst, GLib

import cherrypy

from cc_pathlib import Path

from musich.common import *

# https://lazka.github.io/pgi-docs/Gst-1.0/classes/Element.html

class MusichLocal() :
	def __init__(self, static_dir, catalog_obj) :
		Gst.init(None)

		self.m_sta = static_dir

		self.m_que = QueueLst() # queue, list of pieces to be played
		self.m_hst = HistoryLst() # history, list of pieces already played

		self.m_pos = -1
		self.m_cat = catalog_obj
		self.m_cur = None # name of the track currently played or paused

		self.g = Gst.ElementFactory.make("playbin", "player")

		self.g.connect("about-to-finish", self._about_to_finish)

		self.dev_null = Gst.ElementFactory.make("fakesink", "fakesink")
		self.g.set_property("video-sink", self.dev_null)

		#self.player.set_property("uri", "file://" + "/mnt/workbench/source/musich/test/gstreamer/03.Dam.mp3")

		self.m_bus = self.g.get_bus()
		self.m_bus.add_signal_watch()
		self.m_bus.connect("message", self.on_message)

		# debug mode :
		for pth in (self.m_cat.c_dir / 'sample').glob('*.wav') :
			key = str(pth.relative_to(self.m_cat.c_dir))
			if '4' in key or '5' in key :
				self.m_que.add_after(key)
			if '2' in key or '3' in key :
				self.m_hst.push(key)

		self._play()

	@cherrypy.expose
	def index(self) :
		return (self.m_sta / 'html' / 'local.html').read_text()

	@cherrypy.expose
	def _load_cat(self, * pos, ** nam) :
		cherrypy.response.headers['Content-Type'] = 'text/javascript'
		return (self.m_cat.c_dir / ".database" / "index.json").read_bytes()

	# @cherrypy.expose
	# @cherrypy.tools.json_out()
	# def _load_que(self, * pos, **nam) :
	# 	# cherrypy.response.headers['Content-Type'] = 'text/javascript'
	# 	print(f"MusichLocal._load_que() -> {self.m_que}")
	# 	return self.m_que

	# @cherrypy.expose
	# @cherrypy.tools.json_out()
	# def _load_hst(self, * pos, **nam) :
	# 	# cherrypy.response.headers['Content-Type'] = 'text/javascript'
	# 	print(f"MusichLocal._load_hst() -> {self.m_que}")
	# 	return self.m_hst

	# def is_valid_pos(self, i) :
	# 	return 0 <= i < len(self.m_que)

	# @cherrypy.expose
	# def play_next(self) :
	# 	print(f"MusichLocal.play_next()", self.is_valid_pos(i))
	# 	if self.is_valid_pos(i) :
	# 		self._play( self.m_que.pop(self.m_pos) )

	# @cherrypy.expose
	# def play_next(self) :
	# 	print(f"MusichLocal.play_next()")
	# 	# self.m_que.que_lst.pop(self.m_pos)
	# 	self._play()

	def _about_to_finish(self, * pos, ** nam) :
		self._play()

	def _play(self, m_cur=None) :
		print(f"\x1b[35mMusichLocal._play(\x1b[36m{m_cur}\x1b[35m)\x1b[0m")
		if m_cur is None :
			try :
				m_cur = self.m_que.que_lst.pop(0)
			except :
				pass
		self.m_cur = m_cur

		if self.m_cur is None :
			return

		self.m_hst.push(self.m_cur)

		if not self.m_que :
			for pth in (self.m_cat.c_dir / 'sample').glob('*.wav') :
				key = str(pth.relative_to(self.m_cat.c_dir))
				if '4' in key or '5' in key :
					self.m_que.append(key)

		m_pth = self.m_cat.c_dir / self.m_cur

		print(f"MusichLocal._play_this({m_cur}) --> {self.m_cur}")
		
		self.g.set_state(Gst.State.NULL)
		self.g.set_property("uri", f"file://{m_pth}")
		self.g.set_state(Gst.State.PLAYING)

	def _get_pos_dur(self) :
		position_val, position = self.g.query_position(Gst.Format.TIME)
		duration_val, duration = self.g.query_duration(Gst.Format.TIME)

		if position_val and duration_val :
			pass

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def _get_status(self, * pos, ** nam) :
		print(f"\n\nMusichLocal._get_status({pos}, {nam})")
		#cherrypy.response.headers["Content-Type"] = "text/event-stream;charset=utf-8"
		
		# hst_lst = list()
		last_timestamp = int(nam['last_timestamp']) if 'last_timestamp' in nam else -1
		# for k, v in self.m_hst.items() :
		# 	if v > last_timestap :
		# 		hst_lst.append(k)

		return {
			"cur": self.m_cur,
			"_play_": self.g.get_state(1000).state == Gst.State.PLAYING,
			"que": self.m_que.que_lst,
			"hst": self.m_hst.get_status(last_timestamp),
			"_last_": self.m_hst.hst_lst[-1][1],
			"_pos_": [position, duration,],
		}
		# return f"data: {json.dumps(status)}\n\n"

	# @cherrypy.expose
	# def play_prev(self) :
	# 	self.play_at(self.m_pos - 1)

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def play_next(self, * pos, ** nam) :
		print(f"MusichLocal.play_next()")
		self._play()
		return {
			"cur": self.m_cur,
			"_play_": self.g.get_state(1000).state == Gst.State.PLAYING,
		}

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def play_pause(self) :
		print(f"MusichLocal.play_pause()")
		if self.g.get_state(1000).state == Gst.State.PLAYING :
			self.g.set_state(Gst.State.PAUSED)
			return {
				"cur": self.m_cur,
				'_play_': False,
			}
		else :
			self.g.set_state(Gst.State.PLAYING)
			return {
				"cur": self.m_cur,
				'_play_': True,
			}

	def on_message(self, bus, message):
		t = message.type
		if t == Gst.MessageType.EOS:
			self.g.set_state(Gst.State.NULL)
			print("EOS: %s" % err, debug)
		elif t == Gst.MessageType.ERROR:
			self.g.set_state(Gst.State.NULL)
			err, debug = message.parse_error()
			print("ERROR: %s" % err, debug)

	@cherrypy.expose
	@cherrypy.tools.json_out()
	@cherrypy.tools.json_in()
	def update_queue(self, * pos, ** nam) :
		when, what = cherrypy.request.json
		if when == "next" :
			self.m_que.add_next(what)
		elif when == "after" :
			self.m_que.add_after(what)
		elif when == "now" :
			self._play(what)

		print("\n\n>>> update_queue", pos, nam, cherrypy.request.json, "\n\n")
		return {
			"cur": self.m_cur,
			"que": self.m_que.que_lst,
			"_play_": self.g.get_state(1000).state == Gst.State.PLAYING,
		}

if __name__ == '__main__' :

	MusichLocal._push_notification._cp_config = {'response.stream': True}

	u = MusichLocal()
	u.play_at(0)

	cherrypy.config.update({
		'server.socket_host': '127.0.0.1',
		'server.socket_port': 45081,
	}) # global config

	cherrypy.tree.mount(u, '/')

	cherrypy.engine.start()
	# cherrypy.engine.block()
	print("RUN")
	GLib.MainLoop().run()
