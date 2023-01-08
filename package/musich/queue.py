#!/usr/bin/env python3


class MusichQueue() :
	# utilisé pour la playlist locale, pourrait être utilisé aussi pour la playlist à distance (une fois qu'on aura mis un système d'authentification)

	def __init__(self) :
		self.next_lst = list()
		self.prev_lst = list()
		
	def push_to_end(self, key) :
		self.next_lst.append(key)

	def push_to_next(self, key) :
		self.next_lst = [key,] + self.next_lst

	def pop(self) :
		key = self.next_lst.pop(0)
		self.prev_lst.append(key)
		return key

	@property
	def curr(self) :
		return self.prev_lst[-1]
