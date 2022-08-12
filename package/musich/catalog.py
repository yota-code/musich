#!/usr/bin/env python3

import base64
import datetime
import hashlib
import json
import os
import sqlite3
import sys

from cc_pathlib import Path

import mutagen

encoding_map = {
	'Encoding.LATIN1': 'latin-1',
	'Encoding.UTF16': 'utf-16'
}

# https://id3.org/id3v2.4.0-frames

tag_rename_map = {
	'TXXX:Acoustid Id' : 'acoustid',
	'Acoustid/Id' : 'acoustid',
	'TXXX:SCRIPT' : 'script',
	'TXXX:originalyear' : 'originalyear',
	'TXXX:BARCODE' : 'barcode',
	'TXXX:ASIN' : 'asin',
	'TXXX:CATALOGNUMBER' : 'catalognumber',
	'TXXX:ARTISTS' : 'artists',
	'TENC' : 'encoder',
	'TIT2' : 'title',
	'TSO2' : 'albumartistsort',
	'TSOP' : 'artistsort',
	'TSOA' : 'albumsort',
	'TSRC' : 'isrc',
	'TALB' : 'album',
	'TXXX:Artists' : 'artists',
	'TCON' : 'genre',
	'TSST' : 'setsubtitle',
	'TDRC' : 'originaldate',
	'TDOR' : 'yearrel',
	'TPE1' : 'artist',
	'TPE2' : 'performer',
	'TMED' : 'media',
	'USLT::eng' : 'lyrics.en',
	'TPUB' : 'organization',
	'TLAN' : 'language',
	'TCOM' : 'composer',
	'TIPL' : 'people',
	'TLEN' : 'length',
	'TOAL' : 'originalalbum',
	'TSSE' : 'encoder',
}

tag_delete_set = {
	"barcode", "catalognumber", "asin", "isrc", "encoder", "encoder_options", "encoder_version", "wmfsdkneeded", "wmfsdkversion",
	"engineer", "script", "media", "accurateripdiscid", "length", "rating", "rating"
}

tag_integer_set = {
	"totaldiscs", "totaltracks", "tracknumber", "tracktotal", "originalyear", "yearrel", "discnumber", "disctotal", "length"
}

t_col, t_row = os.get_terminal_size(0)

def _alnum_filter(s) :
	return ''.join( c for c in str(s).lower() if c.isalnum() )

def _recurse_dir(parent_dir, depth=0) :
	for pth in parent_dir.iterdir() :
		if pth.is_file() :
			yield pth
		elif pth.is_dir() :
			print(("--" * (depth)) + '->', pth.name)
			try :
				yield from _recurse_dir(pth, depth + 1)
			except PermissionError :
				pass
		else :
			print(pth)

# un fichier json prend bien moins de place qu'une base de données, et en plus on peut l'envoyer directement

class MusichCatalog() :

	"""
		meta.json : hash -> all meta content, sent to the client
		file.json : hash -> (path, mtime) not known by the client
	"""

	mime = {
		'.mp3' : "audio/mpeg",
		'.flac' : "audio/flac",
		'.ogg' : "audio/ogg",
		'.wav' : "audio/wav",
		'.wma' : "audio/x-ms-wma"
	}

	def __init__(self, catalog_dir) :

		self.e_lst = list( self.mime )
		self.c_dir = catalog_dir.resolve()

		self.meta_pth = (self.c_dir / ".database" / "meta.json")
		self.file_pth = (self.c_dir / ".database" / "file.json")

		self._load()

	def _load(self) :
		self.meta_map = self.meta_pth.load() if self.meta_pth.is_file() else dict()
		self.file_map = self.file_pth.load() if self.file_pth.is_file() else dict()

		self.hash_map = { v[0] : k for k, v in self.file_map.items() }

	def _save(self) :
		self.meta_pth.save(self.meta_map)
		self.file_pth.save(self.file_map)
		
		self.meta_pth.with_suffix('.json.br').save(self.meta_map)
		self.file_pth.with_suffix('.json.br').save(self.file_map)

	def key_to_part(self, key) :
		if (self.c_dir / Path(key).parts[0]).is_symlink() :
			p = Path(Path(key).with_suffix('')).parts[1:]
		else :
			p = Path(Path(key).with_suffix('')).parts
		return '/'.join(p)

	def key_to_path(self, key) :
		return self.c_dir / key

	def key_to_hash(self, key) :
		bin = self.key_to_path(key).read_bytes()
		hsh = hashlib.blake2b(bin, salt=b"#musich", digest_size=24).digest()
		b64 = base64.urlsafe_b64encode(hsh).decode('ascii')
		return f'{b64}.{len(bin):x}'

	def key_to_time(self, key) :
		mtm = int(self.key_to_path(key).stat().st_mtime)
		return mtm

	def key_to_meta(self, key) :
		pth = self.key_to_path(key)

		tag_0_map = dict(mutagen.File(pth))

		try :
			tag_1_map = self.pass_1(tag_0_map)
		except :
			print(tag_0_map)
			raise

		try :
			tag_2_map = self.pass_2(tag_1_map)
		except :
			print(tag_1_map)
			raise

		try :
			tag_3_map = self.pass_3(tag_2_map)
		except :
			print(tag_0_map)
			print(tag_1_map)
			print(tag_2_map)
			raise

		tag_4_map = self.pass_4(tag_3_map)

		tag_4_map['/'] = self.key_to_part(key)

		return tag_4_map

	def pop(self, key) :
		print(f"- {key}")

		hsh, mtm = self.hash_map[key]

		del self.meta_map[hsh]
		del self.file_map[hsh]

		del self.hash_map[key]

	def push(self, key) :
		print(f"+ {key}")

		hsh = self.key_to_hash(key)
		mtm = self.key_to_time(key)

		self.file_map[hsh] = [key, mtm]
		self.meta_map[hsh] = self.key_to_meta(key)

		self.hash_map[key] = hsh

		self.tag_set |= self.meta_map[hsh].keys()


	def scan(self, * suffix_lst, parent_dir=None) :
		""" scan all folders in the catalog folder, return a set of files """
		if parent_dir is None :
			parent_dir = self.c_dir

		print(f"MusichCatalog.scan({suffix_lst}, {parent_dir})")

		return set(
			str(pth.relative_to(self.c_dir))
			for pth in _recurse_dir(parent_dir)
			if pth.suffix.lower() in suffix_lst
		)

	def refresh(self, * suffix_lst, parent_dir=None) :
		print(f"MusichCatalog.refresh({suffix_lst}, {parent_dir})")

		self.tag_set = set()

		if not suffix_lst :
			suffix_lst = list(self.mime)

		key_set = self.scan(* suffix_lst, parent_dir=parent_dir)

		to_be_deleted_set = self.hash_map.keys() - key_set
		for key in to_be_deleted_set :
			self.pop(key)

		for key in key_set :
			pth = self.key_to_path(key)
			if key in self.hash_map :
				hsh, mtm = self.hash_map[key]
				if int(pth.stat().st_mtime) <= mtm :
					print(f"= {key}")
					continue
			else :
				self.push(key)

		self._save()

		Path("tag_lst.txt").write_text('\n'.join(sorted(self.tag_set)))
		








		# self.zero_mtime = self.index_pth.stat().st_mtime

		# self.index_map = self.index_pth.load()
		
		# if parent_dir is None :
		# 	parent_dir = self.c_dir

		# if suffix_lst is None :
		# 	suffix_lst = self.e_lst

		# file_lst = self.scan(parent_dir, suffix_lst)

		# file_set = set(file_lst)

		# to_del_set = self.index_map.keys() - file_set
		# for pth in to_del_set :
		# 	self.pop(pth)

		# to_add_set = file_set - self.index_map.keys()
		# for key in file_set :
		# 	if key in to_add_set or self.zero_mtime <= (self.c_dir / key).stat().st_mtime :
		# 		bin = (self.c_dir / key).read_bytes()
		# 		hsh = base64.urlsafe_b64encode( hashlib.blake2b(bin, salt=b"#musich", digest_size=24).digest() )
		# 		if key not in self.index_map or self.index_map[key]['#'] != hsh :
		# 			self.push(key, hsh)

		# self.index_pth.save(self.index_map)

		# stack = list()
		# for key in sorted(self.index_map) :
		# 	ptn = _alnum_filter(key)
		# 	stack.append([key, self.index_map[key]['#']] + [
		# 		f"{k}={v}"
		# 		for k, v in self.index_map[key].items()
		# 		if k != '#' and _alnum_filter(v) not in ptn
		# 	])

		# self.index_pth.with_suffix('.tsv').save(sorted(stack))




		# tag_0_map = dict()
		# for k, v in mutagen.File(self.c_dir / key).items() :
		# 	tag_0_map[k] = v

		# tag_1_map = self.pass_1(tag_0_map)
		# tag_2_map = self.pass_2(tag_1_map)
		# tag_3_map = self.pass_3(tag_2_map)
		# tag_4_map = self.pass_4(tag_3_map)

		# tag_4_map['#'] = hsh

		# if hsh == "51bf97612c7fb113" :
		# 	print("== 0 ==", tag_0_map)
		# 	print("== 1 ==", tag_1_map)
		# 	print("== 2 ==", tag_2_map)
		# 	print("== 3 ==", tag_3_map)
		# 	print("== 4 ==", tag_4_map)


		# self.index_map[key] = tag_4_map

		# n = 21
		# line = key[-t_col+n:].rjust(t_col-n)
		# print(f"+ \x1b[32m{line}\x1b[0m [\x1b[33m{self.index_map[key]['#']}\x1b[0m]")


		# self.hsh_to_str_map[hsh] = '\t'.join(Path(key).parts)

		return

		if self.location_pth.is_file() :
			for hash, path in self.location_pth.load().items() :
				old_path_map[path] = hash

		k_set = set()

		for n, pth in enumerate( recurse_dir(self.c_dir) ) :
			if pth.suffix.lower() in ['.mp3', '.flac', '.ogg', '.wav', 'wma'] :
				hash = hashlib.blake2b(pth.read_bytes()).hexdigest()[:12]

				key = str( pth.relative_to(self.c_dir) )
				if key in h_map and h_map[key] == hash :
					# the file didn't change, we don't process it at all
					print(f"= \x1b[32m{key}\x1b[0m")
					continue
				else :
					print(f"+ \x1b[31m{key}\x1b[0m")

				k_set.add(key)
				h_map[key] = hash

				t_map = dict()
				for k, v in mutagen.File(pth).items() :
					t_map[k] = v
				self.c_map[key] = t_map

		return k_set


	def update(self) :
		index_pth = Path(self.c_dir / ".database" / "index.json")
		u = index_pth.load()
		for key in u :
			s = set()
			for k, v in u[key].items() :
				if isinstance(v, int) :
					continue
				if v in key :
					continue
				s.add(v)
			u[key] = '\t'.join(s)
		Path(self.c_dir / ".database" / "catalog.json").save(u)

		hash_pth = self.c_dir / ".database" / "hash.txt"
		if hash_pth.is_file() :
			print("update skipped")
			return

		h_map = {p : h for p, h in zip(
			sorted(self.c_map),
			[ h.strip() for h in hash_pth.read_text().splitlines() ] if hash_pth.is_file() else list()
		)}

		k_set = self.scan(h_map)

		with Path("pass_0.txt").open('wt') as fid :
			for key in sorted(k_set) :
				fid.write(f"{key}\t{self.c_map[key]}\n")

		for i in range(4) :

			getattr(self, f"pass_{i+1}")(k_set)

			with Path(f"pass_{i+1}.txt").open('wt') as fid :
				for key in sorted(k_set) :
					fid.write(f"{key}\t{self.c_map[key]}\n")

		h_lst = list()
		for key in sorted(self.c_map) :
			h_lst.append( h_map[key] )
		hash_pth.write_text('\n'.join(h_lst))

		self.index_pth.save(self.c_map)

		return
			
	# def scan(self, h_map) :
	# 	k_set = set()

	# 	for n, pth in enumerate(recurse_dir(self.c_dir)) :
	# 		if pth.suffix.lower() in ['.mp3', '.flac', '.ogg', '.wav', 'wma'] :
	# 			hash = hashlib.blake2b(pth.read_bytes()).hexdigest()[:12]

	# 			key = str( pth.relative_to(self.c_dir) )
	# 			if key in h_map and h_map[key] == hash :
	# 				# the file didn't change, we don't process it at all
	# 				print(f"= \x1b[32m{key}\x1b[0m")
	# 				continue
	# 			else :
	# 				print(f"+ \x1b[31m{key}\x1b[0m")

	# 			k_set.add(key)
	# 			h_map[key] = hash

	# 			t_map = dict()
	# 			for k, v in mutagen.File(pth).items() :
	# 				t_map[k] = v
	# 			self.c_map[key] = t_map

	# 	return k_set

	def pass_1(self, tag_map) :
		res_map = dict()
		for k in tag_map :
			if k in ['metadata_block_picture', 'POPM:Windows Media Player 9 Series'] :
				continue
			v = tag_map[k]
			if isinstance(v, list) : # une liste ? c'est un tag sur plusieurs lignes
				res_map[k] = ';'.join(str(i).strip() for i in v)
			elif hasattr(v, 'mime') and v.mime.startswith("image/") : # une image ? on jette
				pass
			elif hasattr(v, 'encoding') :
				if hasattr(v, 'text') :
					if isinstance(v.text, str) :
						txt = '\n'.join(str(i) for i in (v.text).splitlines())
					elif isinstance(v.text, list) :
						txt = '\n'.join(str(i) for i in v.text)
					res_map[k] = txt
					continue
				elif hasattr(v, 'people') :
					stack = list()
					for f, q in v.people :
						stack.append(f"{f}:{q}")
					res_map[k] = ';'.join(stack)
			elif hasattr(v, 'data') : # un truc binaire ? on jette
				pass
			else :
				print(k, v)
		return res_map

	def pass_2(self, tag_map) :
		# rename tags to be renamed
		res_map = dict()
		
		for tag in tag_map :
			if tag.startswith('TXXX:MusicBrainz ') :
				k = 'musicbrainz_' + ''.join(tag[len('TXXX:MusicBrainz '):].split()).lower()
			elif tag.startswith('MusicBrainz/') :
				k = 'musicbrainz_' + ''.join(tag[len('MusicBrainz/'):].split()).lower()
			elif tag.startswith('TXXX:') :
				k = ''.join(tag[len('TXXX:'):].split()).lower()
			elif tag.startswith('WM/') :
				k = ''.join(tag[len('WM/'):].split()).lower()
			else :
				k = tag

			res_map[k] = tag_map[tag]

		for tag_before, tag_after in tag_rename_map.items() :
			if tag_before in res_map :
				if tag_after in res_map :
					if res_map[tag_before] != res_map[tag_after] :
						# possible duplicate tag with different content
						raise ValueError(f"tag rename {tag_before} -> {tag_after}")
					else :
						del res_map[tag_before]
				else :
					res_map[tag_after] = res_map[tag_before]
					del res_map[tag_before]
		return res_map

	def pass_3(self, tag_map) :
		# delete tags to be deleted
		res_map = dict()
		for k in tag_map :
			u = k.lower()
			if u.startswith('comm:') or u == 'comment' :
				continue
			if u.startswith("musicbrainz_") :
				continue
			if u.startswith("gracenote") :
				continue
			if u in tag_delete_set :
				continue
			res_map[k] = int(tag_map[k]) if k in tag_integer_set else tag_map[k]

		if "track" in res_map and "tracknumber" in res_map :
			del res_map["track"]

		return res_map
				
	def pass_4(self, tag_map) :
		# special processing
		res_map = tag_map.copy()

		if 'TRCK' in res_map :
			tracknumber, tracktotal = None, None
			if '/' in res_map['TRCK'] :
				tracknumber, tracktotal = [int(i) for i in res_map['TRCK'].split('/')]
			else :
				tracknumber = int(res_map['TRCK'])
			if tracknumber is not None :
				res_map['tracknumber'] = tracknumber
				del res_map['TRCK']
			if tracktotal is not None :
				res_map['tracktotal'] = tracktotal

		if 'TPOS' in res_map :
			discnumber, disctotal = None, None
			if '/' in res_map['TPOS'] :
				discnumber, disctotal = [int(i) for i in res_map['TPOS'].split('/')]
			else :
				discnumber = int(res_map['TPOS'])
			if discnumber is not None :
				res_map['discnumber'] = discnumber
				del res_map['TPOS']
			if disctotal is not None :
				res_map['disctotal'] = disctotal

		if 'releasetype' in res_map :
			res_map['releasetype'] = res_map['releasetype'].replace('/', ';')

		return res_map



		# 		if tag_before in self.meta_map :
		# 				tag_after = tag_rename_map[tag_before]
		# 				if tag_after in t_map :
		# 					if t_map[tag_before] != t_map[tag_after] :
		# 						raise ValueError(f"tag rename {tag_before} -> {tag_after}")
		# 					else :
		# 						print(f"extra {tag_before}")
		# 						del t_map[tag_before]
		# 				else :
		# 					t_map[tag_after] = t_map[tag_before]
		# 					del t_map[tag_before]

		# 		for tag in list(t_map) :
		# 			# remove comments (often contains crap)
		# 			if tag.startswith('COMM:') or tag == 'Comment' :
		# 				del t_map[tag]

		# 		if 'TRCK' in t_map :
		# 			tracknumber, tracktotal = None, None
		# 			if '/' in t_map['TRCK'] :
		# 				tracknumber, tracktotal = [int(i) for i in t_map['TRCK'].split('/')]
		# 			else :
		# 				tracknumber = int(t_map['TRCK'])
		# 			if tracknumber is not None :
		# 				t_map['tracknumber'] = tracknumber
		# 				del t_map['TRCK']
		# 			if tracktotal is not None :
		# 				t_map['tracktotal'] = tracktotal

		# 		if 'TPOS' in t_map :
		# 			discnumber, disctotal = None, None
		# 			if '/' in t_map['TPOS'] :
		# 				discnumber, disctotal = [int(i) for i in t_map['TPOS'].split('/')]
		# 			else :
		# 				discnumber = int(t_map['TPOS'])
		# 			if discnumber is not None :
		# 				t_map['discnumber'] = discnumber
		# 				del t_map['TPOS']
		# 			if disctotal is not None :
		# 				t_map['disctotal'] = disctotal
				
		# 		for tag in tag_integer_set :
		# 			if tag in t_map :
						

		# 	self.meta_map[key] = t_map

		# with Path("3_pass.txt").open('wt') as fid :
		# 	for key in sorted(self.meta_map) :
		# 		fid.write(f"{key}\t{self.meta_map[key]}\n")


		# return

		# self.third_pass_db.save(t_map, filter_opt={"verbose":True})
		# (self.c_dir / '.database/meta.json.br').save(t_map)

		# for key in t_map :
		# 	for tag in list(t_map) :
		# 		if tag.startswith("musicbrainz_") or tag in tag_delete_lst :
		# 			del t_map[tag]

		# stack = list()
		# for p in sorted(t_map) :
		# 	line = [p,] + [f"{k}={v}" for k, v in t_map[p].items()]
		# 	stack.append(line)

	# def scan(self) :
	# 	for n, pth in enumerate(recurse_dir(self.c_dir)) :
	# 		if pth.suffix.lower() in ['.mp3', '.flac', '.ogg'] :
	# 			rel = pth.relative_to(self.c_dir)
	# 			try :
	# 				m = mutagen.File(pth)
	# 				stack = list()
	# 				for k in m :
	# 					if isinstance(m[k], mutagen.id3.MCDI) :
	# 						continue
	# 					if ( isinstance(m[k], list) ) :
	# 						v = ';'.join(m[k])
	# 					else :
	# 						if hasattr(m[k], 'mime') and m[k].mime == "image/jpeg" :
	# 							continue
	# 						v = m[k]
	# 					stack.append([k, v])
	# 					if isinstance(v, bytes) :
	# 						print(pth, k)
	# 						sys.exit(0)

	# 				stack = sorted(stack)
	# 				self.database[str(rel)] = '\t'.join(f"{k}:{v}" for k, v in stack)
	# 				# print("{0}\t{1}".format(n, rel))
	# 			except mutagen.mp3.HeaderNotFoundError :
	# 				print("{0}\t{1}".format(n, rel), file=sys.stderr)

	# def save(self, pth) :

	# 	print("---", pth.resolve())

	# 	db = (self.c_dir / "database.json.br").load()

	# 	stack = list()
	# 	for n, k in enumerate(sorted(db)) :
	# 		stack.append(f'{k}\t{db[k]}')

	# 	pth.write_text('\n'.join(stack))
