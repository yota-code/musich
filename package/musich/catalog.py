#!/usr/bin/env python3

import base64
import collections
import datetime
import hashlib
import json
import os
# from re import T
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
		file.json : hash -> (key, mtime) not known by the client

		in c_dir, the first level directory must contains not information about the music
		c_dir / key is always a music file

		hash_map : key -> (path, mtime)
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

		self.meta_pth = (self.c_dir / ".database" / "meta.json")
		self.file_pth = (self.c_dir / ".database" / "file.json")
		# self.search_pth = (self.c_dir / ".database" / "search.json")
		# self.album_pth = (self.c_dir / ".database" / "album.json")

		self._load()

	def _load(self) :
		self.meta_map = self.meta_pth.load() if self.meta_pth.is_file() else dict()
		self.file_map = self.file_pth.load() if self.file_pth.is_file() else dict()
		# self.search_map = self.search_pth.load() if self.search_pth.is_file() else dict()

		self.hash_map = { v[0] : (k, v[1]) for k, v in self.file_map.items() }

	def _prep_album(self) :
		self.album_map = collections.defaultdict(set)

		for k in self.meta_map :
			u = '/'.join(self.meta_map[k]['/'][:-1])
			self.album_map[u].add((self.meta_map[k].get('tracknumber', 0), self.meta_map[k]['/'][-1], k))

		for u in self.album_map :
			self.album_map[u] = [(b, c) for a, b, c in sorted(self.album_map[u])]

		del self.album_map[""]

	def _save(self) :
		self.meta_pth.save(self.meta_map)
		self.file_pth.save(self.file_map)

		self.meta_pth.with_suffix('.json.br').save(self.meta_map)
		self.file_pth.with_suffix('.json.br').save(self.file_map)

		# self.album_pth.save(self.album_map)
		# self.search_pth.save(self.search_map)
		# self.search_pth.with_suffix('.json.br').save(self.search_map)

	def key_to_part(self, key) :
		return Path(key).with_suffix('').parts[1:]

	def key_to_path(self, key) :
		return self.c_dir / key

	def hash_to_path(self, hsh) :
		return self.c_dir / self.file_map[hsh][0]

	def key_to_hash(self, key) :
		bin = self.key_to_path(key).read_bytes()
		#TODO: on pourrait passer à 18 bytes (144 bits)
		hsh = hashlib.blake2b(bin, salt=b"#musich", digest_size=24).digest()
		b64 = base64.urlsafe_b64encode(hsh).decode('ascii')
		return f'{b64}.{len(bin):X}'

	def key_to_time(self, key) :
		return int(self.key_to_path(key).stat().st_mtime)

	def key_to_size(self, key) :
		return int(self.key_to_path(key).stat().st_size)

	def hsh_to_search(self, hsh) :
		s_lst = [' '.join(self.meta_map[hsh]["/"]),]
		for k in self.meta_map[hsh] :
			if k == "/" :
				continue
			m = str(self.meta_map[hsh][k])
			for s in s_lst[:] :
				if m in s :
					break
			else :
				s_lst.append(m)
		return s_lst[0] + '\t' + ' '.join(s_lst[1:])

	def key_to_meta(self, key) :
		pth = self.key_to_path(key)

		tag_lst = list()
		try :
			tag_lst.append( dict(mutagen.File(pth)) )
			pass_lst = [
				getattr(self, n)
				for n in sorted(m for m in dir(self) if m.startswith('pass_'))
			]
			for func in pass_lst :
				tag_lst.append(func(tag_lst[-1]))
		except :
			print(tag_lst)
			raise
		
		tag_lst[-1]['/'] = self.key_to_part(key)

		return tag_lst[-1]

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
		self.search_map[hsh] = self.hsh_to_search(hsh)

		self.hash_map[key] = [hsh, mtm]

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

		for key in sorted(key_set) :
			pth = self.key_to_path(key)
			if key in self.hash_map :
				try :
					hsh, mtm = self.hash_map[key]
				except :
					print(self.hash_map[key])
					raise
				if int(pth.stat().st_mtime) <= mtm :
					print(f"= {key}")
					continue
			else :
				self.push(key)

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
