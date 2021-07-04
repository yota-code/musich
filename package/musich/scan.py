#!/usr/bin/env python3

import sys
import os

from cc_pathlib import Path

import mutagen

def recurse_dir(parent) :
	for pth in parent.iterdir() :
		if pth.is_file() :
			yield pth
		elif pth.is_dir() :
			try :
				yield from recurse_dir(pth)
			except PermissionError :
				pass
		else :
			print(pth)

encoding_map = {
	'Encoding.LATIN1': 'latin-1',
	'Encoding.UTF16': 'utf-16'
}

tag_rename_map = {
	'TXXX:Acoustid Id' : 'acoustid_id',
	'TXXX:MusicBrainz Album Artist Id' : 'musicbrainz_albumartistid',
	'TXXX:MusicBrainz Album Id' : 'musicbrainz_albumid',
	'TXXX:MusicBrainz Album Release Country' : 'releasecountry',
	'TXXX:MusicBrainz Album Status' : 'releasestatus',
	'TXXX:MusicBrainz Album Type' : 'releasetype',
	'TXXX:MusicBrainz Artist Id' : 'musicbrainz_artistid',
	'TXXX:MusicBrainz Release Group Id' : 'musicbrainz_releasegroupid',
	'TXXX:MusicBrainz Release Track Id' : 'musicbrainz_releasetrackid',
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
	'TSRC' : 'isrc',
	'TALB' : 'album',
	'TXXX:Artists' : 'artists',
	'TCON' : 'genre',
	'TDRC' : 'originaldate',
	'TDOR' : 'yearrel',
	'TPE1' : 'artist',
	'TPE2' : 'performer',
	'TMED' : 'media',
	'USLT::eng' : 'lyrics',
	'TPUB' : 'organization',
	'TLAN' : 'language',
	'TCOM' : 'composer',
	'TIPL' : 'people',
	'TLEN' : 'length'
}

tag_delete_lst = ["barcode", "catalognumber", "asin", "isrc", "encoder", "encoder_options", "encoder_version", "engineer", "script", "media", "accurateripdiscid", "acoustid_id", "length"]

tag_integer_set = {
	"totaldiscs", "totaltracks", "tracknumber", "tracktotal", "originalyear", "yearrel", "discnumber", "disctotal", "length"
}

t_col, t_row = os.get_terminal_size(0)

class MusicDatabase() :

	def __init__(self, catalog_dir) :

		self.catalog_dir = catalog_dir.resolve()
		self.database = dict()

		self.first_pass_db = self.catalog_dir / ".database/pass_1.pickle"
		self.second_pass_db = self.catalog_dir / ".database/pass_2.json"
		self.third_pass_db = self.catalog_dir / ".database/pass_3.json"

		if not self.first_pass_db.is_file() :
			self.first_pass()

		if not self.second_pass_db.is_file() :
			self.second_pass()

		if not self.third_pass_db.is_file() :
			self.third_pass()
			
	def first_pass(self) :
		scan_map = dict()
		print(f'\x1b[K\x1b[Afirst_pass() :: in progress ...')
		for n, pth in enumerate(recurse_dir(self.catalog_dir)) :
			if pth.suffix.lower() in ['.mp3', '.flac', '.ogg'] :
				print(f'\x1b[A\x1b[Kfirst_pass: {pth.relative_to(self.catalog_dir)}'[:t_col - 4])
				rel = pth.relative_to(self.catalog_dir)
				tmp_map = dict()
				for k, v in mutagen.File(pth).items() :
					tmp_map[k] = v
				scan_map[str(rel)] = tmp_map
		self.first_pass_db.save(scan_map)
		print(f'\x1b[K\x1b[Afirst_pass() :: DONE')

	def second_pass(self) :
		scan_map = self.first_pass_db.load()
		data_map = dict()
		for k in sorted(scan_map) :
			tmp_map = dict()
			for m in scan_map[k] :
				if m in ['metadata_block_picture', 'POPM:Windows Media Player 9 Series'] :
					continue
				v = scan_map[k][m]
				if isinstance(v, list) : # une liste ? c'est un tag sur plusieurs lignes
					tmp_map[m] = ';'.join(str(i) for i in v)
				elif hasattr(v, 'mime') and v.mime == "image/jpeg" : # une image ? on jette
					pass
				elif hasattr(v, 'encoding') :
					if hasattr(v, 'text') :
						if isinstance(v.text, str) :
							txt = '\n'.join(str(i) for i in (v.text).splitlines())
						elif isinstance(v.text, list) :
							txt = '\n'.join(str(i) for i in v.text)
						tmp_map[m] = txt
						continue
					elif hasattr(v, 'people') :
						stack = list()
						for f, q in v.people :
							stack.append(f"{f}:{q}")
						tmp_map[m] = ';'.join(stack)
				elif hasattr(v, 'data') : # un truc binaire ? on jette
					pass
				else :
					try :
						print(m, v.__dict__.keys(), repr(v))
					except :
						print(m, v)

			data_map[k] = tmp_map

		self.second_pass_db.save(data_map, filter_opt={"verbose":True})

	def third_pass(self) :
		data_map = self.second_pass_db.load()

		for pth in data_map :
			for tag_before in tag_rename_map :
				if tag_before in data_map[pth] :
					tag_after = tag_rename_map[tag_before]
					if tag_after in data_map[pth] :
						if data_map[pth][tag_before] != data_map[pth][tag_after] :
							raise ValueError(f"tag rename {tag_before} -> {tag_after}")
						else :
							print(f"extra {tag_before}")
							del data_map[pth][tag_before]
					else :
						data_map[pth][tag_after] = data_map[pth][tag_before]
						del data_map[pth][tag_before]

			for tag in list(data_map[pth]) :
				# remove comments (often contains crap)
				if tag.startswith('COMM:') or tag == 'Comment' :
					del data_map[pth][tag]

			if 'TRCK' in data_map[pth] :
				tracknumber, tracktotal = None, None
				if '/' in data_map[pth]['TRCK'] :
					tracknumber, tracktotal = [int(i) for i in data_map[pth]['TRCK'].split('/')]
				else :
					tracknumber = int(data_map[pth]['TRCK'])
				if tracknumber is not None :
					data_map[pth]['tracknumber'] = tracknumber
					del data_map[pth]['TRCK']
				if tracktotal is not None :
					data_map[pth]['tracktotal'] = tracktotal

			if 'TPOS' in data_map[pth] :
				discnumber, disctotal = None, None
				if '/' in data_map[pth]['TPOS'] :
					discnumber, disctotal = [int(i) for i in data_map[pth]['TPOS'].split('/')]
				else :
					discnumber = int(data_map[pth]['TPOS'])
				if discnumber is not None :
					data_map[pth]['discnumber'] = discnumber
					del data_map[pth]['TPOS']
				if disctotal is not None :
					data_map[pth]['disctotal'] = disctotal
			
			for tag in tag_integer_set :
				if tag in data_map[pth] :
					data_map[pth][tag] = int(data_map[pth][tag])

		self.third_pass_db.save(data_map, filter_opt={"verbose":True})
		(self.catalog_dir / '.database/meta.json.br').save(data_map)

		for pth in data_map :
			for tag in list(data_map[pth]) :
				if tag.startswith("musicbrainz_") or tag in tag_delete_lst :
					del data_map[pth][tag]

		stack = list()
		for p in sorted(data_map) :
			line = [p,] + [f"{k}={v}" for k, v in data_map[p].items()]
			stack.append(line)

		(self.catalog_dir / '.database/list.tsv.br').save(stack)

	# def scan(self) :
	# 	for n, pth in enumerate(recurse_dir(self.catalog_dir)) :
	# 		if pth.suffix.lower() in ['.mp3', '.flac', '.ogg'] :
	# 			rel = pth.relative_to(self.catalog_dir)
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

	# 	db = (self.catalog_dir / "database.json.br").load()

	# 	stack = list()
	# 	for n, k in enumerate(sorted(db)) :
	# 		stack.append(f'{k}\t{db[k]}')

	# 	pth.write_text('\n'.join(stack))

if __name__ == '__main__' :
	catalog_dir = Path(os.environ["MUSICH_catalog_DIR"])
	# music_library = Path("/media/yoochan/front/music/library/__library_old__/Alanis Morrisette/Feat On Scraps/")

	u = MusicDatabase(catalog_dir)
	# u.save(Path('./data/__local__.tsv'))

	# txt = Path('./database.txt').read_text()
	# print(txt)
