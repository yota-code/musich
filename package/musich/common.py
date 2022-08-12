#!/usr/bin/env python3

import datetime

class HistoryLst() :
	def __init__(self, max_length=1024) :
		self.zero = datetime.datetime.now()

		self.max_length = max_length
		self.hst_lst = list()

	def push(self, key) :

		hst_lst = list()
		for k, t in self.hst_lst :
			if k != key :
				hst_lst.append((k, t))
		hst_lst.append((key, self.timestamp))

		self.hst_lst = hst_lst[-self.max_length:]

	@property
	def timestamp(self) :
		return int( (datetime.datetime.now() - self.zero).total_seconds() * 1000.0 )

	def get_status(self, last_timestamp=-1) :
		hst_lst = list()
		for k, t in reversed(self.hst_lst) :
			if t <= last_timestamp :
				break
			hst_lst.append(k)
		return hst_lst

class QueueLst() :
	def __init__(self) :
		self.que_lst = list()

	def add_next(self, key) :
		self.que_lst.insert(0, key)

	def add_after(self, key) :
		self.que_lst.append(key)
