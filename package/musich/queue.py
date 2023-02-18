#!/usr/bin/env python3

import os

from cc_pathlib import Path

class MusichQueue() :
	""" this object manage two lists : 
	
	- self.prev_lst or the history, store a list of already played tracks, without duplicates
	- self.next_lst or the queue, store a list of track to be played
	
	"""
	# utilisé pour la playlist locale uniquement, les mises à jour sont sauvegardées

	max_size = 256

	def __init__(self) :
		self.q_pth = Path(os.environ["MUSICH_catalog_DIR"]).resolve() / ".database" / "queue.json"

		self.v_next = 0
		self.v_prev = 0

	def _inc_prev(self) :
		self.v_prev = (self.v_prev + 1) & 0xFFFF

	def _inc_next(self) :
		self.v_next = (self.v_next + 1) & 0xFFFF

	def __enter__(self) :
		if self.q_pth.is_file() :
			q_map = self.q_pth.load()
			self.prev_lst = q_map['prev']
			self.next_lst = q_map['next']
			self._inc_next()
			self._inc_prev()
		else :
			self.next_lst = list()
			self.prev_lst = list()
		return self

	def __exit__(self, exc_type, exc_value, traceback) :
		self.q_pth.save({
			'prev': self.prev_lst,
			'next': self.next_lst
		})

	def push_to_end(self, hsh) :
		""" add an element as the end of the queue """
		self.next_lst.append(hsh)

	def push_to_next(self, hsh) :
		""" add an element at the begining of the queue """
		self.next_lst = [hsh,] + self.next_lst
		self._inc_next()

	def pull(self, hsh, index) :
		""" move an element form the queue """
		if hsh in self.next_lst :
			try :
				if self.next_lst[index] == hsh :
					self.next_lst = self.next_lst[:index] + self.next_lst[index+1:]
					self._inc_next()
			except IndexError :
				pass

	def pop(self) :
		# return the first element of the queue, or None if the queue is empty
		try :
			curr = self.next_lst.pop(0)
		except IndexError :
			return None

		self.prev_lst = [m for m in self.prev_lst if m != curr][-self.max_size+1:]
		self.prev_lst.append(curr)

		self._inc_next()
		self._inc_prev()

		return curr

	def __bool__(self) :
		return len(self.next_lst) != 0

	@property
	def curr(self) :
		return self.prev_lst[-1]
