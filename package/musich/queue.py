#!/usr/bin/env python3


class MusichQueue() :
	# utilisé pour la playlist locale, pourrait être utilisé aussi pour la playlist à distance (une fois qu'on aura mis un système d'authentification)

	max_size = 96

	def __init__(self, save_pth=None) :
		self.save_pth = save_pth

		if save_pth is not None and save_pth.is_file() :
			save_map = save_pth.load()
			self.next_lst = save_map['next']
			self.prev_lst = save_map['prev']
		else :
			self.next_lst = list()
			self.prev_lst = list()
		
	def push_to_end(self, key) :
		self.next_lst.append(key)

	def push_to_next(self, key) :
		self.next_lst = [key,] + self.next_lst

	def pop(self) :
		# return one element of the queue, or None if the queue is empty
		try :
			k = self.next_lst.pop(0)
		except IndexError :
			return None

		self.prev_lst = [m for m in self.prev_lst[-self.max_size+1:] if m != k]
		self.prev_lst.append(k)

		return k

	def __bool__(self) :
		return len(self.next_lst) != 0

	@property
	def curr(self) :
		return self.prev_lst[-1]
