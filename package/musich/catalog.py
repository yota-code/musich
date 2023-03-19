#!/usr/bin/env python3

import base64
import collections
import datetime
import dbm.gnu
import hashlib
import json
import math
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
	"engineer", "script", "media", "accurateripdiscid", "length", "rating", "rating", "notes"
}

tag_integer_set = {
	"totaldiscs", "totaltracks", "tracknumber", "tracktotal", "originalyear", "yearrel", "discnumber", "disctotal", "length"
}

t_col, t_row = os.get_terminal_size(0)

def _alnum_filter(s) :
	return ''.join( c for c in str(s).lower() if c.isalnum() )


# un fichier json prend bien moins de place qu'une base de données, et en plus on peut l'envoyer directement

class MusichCatalog() :
	def __init__(self, catalog_dir) :
		self.c_dir = catalog_dir
		self.c_pth = (self.c_dir / ".database" / "file.dbm")
		self.c_dbm = dbm.gnu.open(str(self.c_pth), 'ru')

	def __getitem__(self, key) :
		return self.c_dbm[key.encode('utf8')].decode('utf8')

class MusichScanner() :
	"""
		meta.json : hash -> all meta content, sent to the client
		file.json : hash -> (key, mtime) not known by the client

		in c_dir, the first level directory must contains not information about the music
		c_dir / key is always a music file

	"""

	mime = {
		'.mp3' : "audio/mpeg",
		'.flac' : "audio/flac",
		'.ogg' : "audio/ogg",
		'.wav' : "audio/wav",
		'.wma' : "audio/x-ms-wma"
	}

	def __init__(self) :

		self.c_dir = Path(os.environ["MUSICH_catalog_DIR"]).resolve()
		self.e_lst = list(self.mime)

		self.meta_pth = self.c_dir / ".database" / "meta.json"
		self.scan_pth = self.c_dir / ".database" / "scan.tsv"
		self.file_pth = self.c_dir / ".database" / "file.dbm"

		self._load()

	def _load(self) :
		# hsh => { field: metadata, ... }
		self.meta_map = self.meta_pth.load() if self.meta_pth.is_file() else dict()

		# pth => fsize, mtime
		self.scan_map = {
			pth : (int(fsize), int(mtime)) for pth, fsize, mtime in self.scan_pth.load()
		} if self.scan_pth.is_file() else dict()

		# pth => hsh
		self.file_map = dict()
		if self.file_pth.is_file() :
			with dbm.gnu.open(str(self.file_pth), 'ru') as db :
				for key in db.keys() :
					self.file_map[db[key].decode('utf8')] = key.decode('utf8')

	# def _prep_album(self) :
	# 	self.album_map = collections.defaultdict(set)

	# 	for k in self.meta_map :
	# 		u = '/'.join(self.meta_map[k]['/'][:-1])
	# 		self.album_map[u].add((self.meta_map[k].get('tracknumber', 0), self.meta_map[k]['/'][-1], k))

	# 	for u in self.album_map :
	# 		self.album_map[u] = [(b, c) for a, b, c in sorted(self.album_map[u])]

	# 	del self.album_map[""]

	def _save(self) :
		self.meta_pth.save(self.meta_map)
		self.meta_pth.with_suffix('.json.br').save(self.meta_map)

		scan_lst = [
			[pth, fsize, mtime]
			for pth, (fsize, mtime) in self.scan_map.items()
		]
		self.scan_pth.save(scan_lst)

		dbm_pth = self.file_pth.with_suffix('.dbm')
		with dbm.gnu.open(str(dbm_pth), 'nf') as db :
			for path, key in self.file_map.items() :
				db[key.encode('utf8')] = path.encode('utf8')
			db.reorganize()
			db.sync()

	def pth_to_part(self, pth) :
		return Path(pth).with_suffix('').parts[1:]

	# def key_to_path(self, key) :
	# 	return self.c_dir / key

	# def hash_to_path(self, hsh) :
	# 	return self.c_dir / self.file_map[hsh][0]

	def pth_to_hash(self, pth) :
		data = (self.c_dir / pth).read_bytes()
		#TODO: on pourrait passer à 18 bytes (144 bits)
		hsh = hashlib.blake2b(data, salt=b"#musich", digest_size=24).digest()
		b64 = base64.urlsafe_b64encode(hsh).decode('ascii')
		return f'{b64}.{len(data):X}'

	def pth_to_stat(self, pth) :
		u = (self.c_dir / pth).stat()
		return u.st_size, int(math.ceil(u.st_mtime))

	# def hsh_to_search(self, hsh) :
	# 	s_lst = [' '.join(self.meta_map[hsh]["/"]),]
	# 	for k in self.meta_map[hsh] :
	# 		if k == "/" :
	# 			continue
	# 		m = str(self.meta_map[hsh][k])
	# 		for s in s_lst[:] :
	# 			if m in s :
	# 				break
	# 		else :
	# 			s_lst.append(m)
	# 	return s_lst[0] + '\t' + ' '.join(s_lst[1:])

	def pth_to_meta(self, pth) :
		tag_lst = list()
		try :
			tag_lst.append( dict(mutagen.File(self.c_dir / pth)) )
			pass_lst = [
				getattr(self, n)
				for n in sorted(m for m in dir(self) if m.startswith('pass_'))
			]
			for func in pass_lst :
				tag_lst.append(func(tag_lst[-1]))
		except :
			print(tag_lst)
			raise
		
		tag_lst[-1]['/'] = self.pth_to_part(pth)

		return tag_lst[-1]

	def pop(self, pth) :
		print(f"- {pth}")

		key = self.file_map[pth]
		del self.meta_map[key]

		del self.file_map[pth]

	def push(self, pth) :
		print(f"+ {pth}")

		hsh = self.pth_to_hash(pth)
		fsize, mtime = self.pth_to_stat(pth)

		self.file_map[pth] = hsh
		self.meta_map[hsh] = self.pth_to_meta(pth)

		self.tag_set |= self.meta_map[hsh].keys()

	def scan(self, parent_dir, suffix_lst, depth=0) :
		for pth in parent_dir.iterdir() :
			if pth.is_file() and pth.suffix.lower() in suffix_lst :
				p = str(pth.relative_to(self.c_dir))
				yield p, self.pth_to_stat(p)
			elif pth.is_dir() :
				print(("- " * (depth)) + '>', pth.name)
				try :
					yield from self.scan(pth, suffix_lst, depth + 1)
				except PermissionError :
					pass
			else :
				print(pth)

	# def scan(self, * suffix_lst, parent_dir=None) :
	# 	""" scan all folders in the catalog folder, return a set of files, with last modification times """
	# 	if parent_dir is None :
	# 		parent_dir = self.c_dir

	# 	print(f"MusichCatalog.scan({suffix_lst}, {parent_dir})")

	# 	return {
	# 		str(pth.relative_to(self.c_dir))
	# 		for pth in _recurse_dir(parent_dir)
	# 		if pth.suffix.lower() in suffix_lst
	# 	}

	def refresh(self) :
		self.tag_set = set()

		scan_old = self.scan_map
		scan_new = {p : s for p, s in self.scan(self.c_dir, list(self.mime))}

		to_be_deleted_set = self.file_map.keys() - scan_new.keys()

		to_be_added_set = scan_new.keys() - self.file_map.keys()
		to_be_modified_set = {
			p for p in scan_new.keys() & scan_old.keys()
			if scan_old[p] != scan_new[p]
		}

		for pth in sorted(to_be_deleted_set) :
			self.pop(pth)

		for pth in sorted(to_be_added_set | to_be_modified_set) :
			self.push(pth)

		self.scan_map = scan_new

		self._save()

		Path("tag_lst.txt").write_text('\n'.join(sorted(self.tag_set)))

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
