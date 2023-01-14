#!/usr/bin/env python3

import enum

import gi

"""
https://github.com/deepakg202/PyGObject-Player/blob/master/player.py
https://brettviren.github.io/pygst-tutorial-org/pygst-tutorial.html
"""

gi.require_version('Gst', '1.0')

from gi.repository import Gst, GLib

class ToggleMode(enum.IntEnum):
	STOP = -1
	PAUSE = 0
	PLAY = 1
	AUTO = 2

class MusichPlayer() :
	""" code for the local player backend """
	def __init__(self, catalog_obj, queue_obj) :

		Gst.init(None)

		self.play_track = None
		self.play_status = None

		self.m_cat = catalog_obj
		self.m_que = queue_obj

		self.gst = Gst.ElementFactory.make("playbin", "player")
		self.gst.connect("about-to-finish", self._about_to_finish)
		self.dev_null = Gst.ElementFactory.make("fakesink", "fakesink")
		self.gst.set_property("video-sink", self.dev_null)

		self.bus = self.gst.get_bus()
		self.bus.add_signal_watch()
		self.bus.connect("message", self._on_message)

		self.pop()

	def _about_to_finish(self, * pos, ** nam) :
		GLib.idle_add(self.pop)
		#self.pop()

	def _on_message(self, bus, msg):
		# callback
		t = msg.type
		if t == Gst.MessageType.EOS:
			self.gst.set_state(Gst.State.NULL)
			print(f"EOS: {bus} {msg}")
		elif t == Gst.MessageType.ERROR:
			self.gst.set_state(Gst.State.NULL)
			err, debug = msg.parse_error()
			print(f"ERROR: {bus} {msg}")

	def get_duration(self) :
		duration_val, duration = self.gst.query_duration(Gst.Format.TIME)
		return round(duration * 1e-6) if duration_val else None

	def get_position(self) :
		position_val, position = self.gst.query_position(Gst.Format.TIME)
		return round(position * 1e-6) if position_val else None

	def set_position(self, value_ms) :
		self.gst.seek_simple(Gst.Format.TIME,  Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, value_ms * Gst.MSECOND)

	def jump_to(self, time) :
		pass

	def pop(self) :
		# pick the next stong and start playing
		hsh = self.m_que.pop()

		if hsh is None :
			print(f"\x1b[35mMusichLocal.play(\x1b[33mEMPTY QUEUE\x1b[35m)\x1b[0m")
			self.play_track = None
			self.gst.set_state(Gst.State.NULL)
			return

		m_pth = self.m_cat.hash_to_path(hsh)
		print(f"\x1b[35mMusichLocal.play(\x1b[36m{m_pth}\x1b[35m)\x1b[0m")
		
		self.play_track = None
		self.gst.set_state(Gst.State.NULL)
		self.gst.set_property("uri", f"file://{m_pth}")
		self.gst.set_state(Gst.State.PLAYING)
		self.play_track = hsh

	def toggle(self, mode=ToggleMode.AUTO) :

		if mode == ToggleMode.PLAY :
			m = Gst.State.PLAYING
		elif mode == ToggleMode.PAUSE :
			m = Gst.State.PAUSED
		elif mode == ToggleMode.AUTO :
			if self.gst.get_state(1000).state == Gst.State.PLAYING :
				m = Gst.State.PAUSED
			else :
				m = Gst.State.PLAYING
		elif mode == ToggleMode.STOP :
			self.play_track = None
			m = Gst.State.NULL

		self.gst.set_state(m)

		self.play_status = None if (m == Gst.State.NULL) else m == Gst.State.PLAYING

		return self.play_status

	def loop(self) :
		self.m_loop = GLib.MainLoop()
		self.m_loop.run()

if __name__ == '__main__' :

	import threading

	import musich.catalog
	import musich.queue

	gi.require_version("Gtk", "3.0")
	from gi.repository import Gtk

	q = musich.queue.MusichQueue()
	c = musich.catalog.MusichCatalog()

	m_lst = list()
	for k, (pth, mtime) in c.file_map.items() :
		if pth.endswith('.wav') :
			m_lst.append((pth, k))

	m_lst = [k for pth, k in sorted(m_lst)]
	q.prev_lst = m_lst[:5]
	q.next_lst = m_lst[5:8]

	u = MusichPlayer(c, q)

	class MiniPlayer(Gtk.Window) :
		# https://python-gtk-3-tutorial.readthedocs.io/en/latest/
	
		def __init__(self):
			Gtk.Window.__init__(self, title="MiniPlayer")

			Gtk.Window.set_default_size(self, 400, 125)
			Gtk.Window.set_position(self, Gtk.WindowPosition.CENTER)

			self.box = Gtk.Box(spacing=6)
			self.add(self.box)

			b_lst = ['play', 'pause', 'play/pause', 'next']
			p_lst = [Gtk.Button(label=b) for b in b_lst]
			_ = [p.connect("clicked", self.when_clicked) for p in p_lst]
			_ = [self.box.pack_start(p, True, True, 0) for p in p_lst]

		def when_clicked(self, button):
			label = button.get_label()
			if label == 'play' :
				u.toggle(ToggleMode.PLAY)
			elif label == 'pause' :
				u.toggle(ToggleMode.PAUSE)
			elif label == 'play/pause' :
				u.toggle(ToggleMode.AUTO)
			if label == 'next' :
				u.pop()


	window = MiniPlayer()
	window.connect("delete-event", Gtk.main_quit)
	window.show_all()

	u.loop()	