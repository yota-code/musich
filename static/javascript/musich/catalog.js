
class MusichCatalog {

	/* the catalog is used both in remote and local

	it downloads the meta.json only and rebuild the search_map and tree_map

	*/

	constructor() {
		this.meta_obj = new Object();

		this.search_map = new Map();
		this.tree_map = new Map();

		this.is_loaded = false;
	}

	load() {
		// retrieve the meta.json(.br) file which contains
		return prom_get_JSON("_get_meta").then((obj) => {
			// drop it in this.meta_obj directly
			this.meta_obj = obj;

			this.prep_tree();
			this.prep_search();

			// confirm everything is loaded
			this.is_loaded = true;
		});
	}

	prep_tree() {
		for (let [hsh, meta] of Object.entries(this.meta_obj)) {
			if ( meta.hasOwnProperty('/') ) {
				var pth_lst = meta['/'];
				let tmp_map = this.tree_map;
				for (let part of pth_lst.slice(0,-1)) {
					if (! tmp_map.has(part)) {
						let new_map = new Map();
						tmp_map.set(part, new_map);
						tmp_map = new_map;
					} else {
						tmp_map = tmp_map.get(part);
					}
				}
				var track_no = (meta.hasOwnProperty('tracknumber')) ? (meta['tracknumber']) : (0);
				tmp_map.set(meta['/'].last(), [track_no, hsh]);
			}
		}
		console.log(">>> prep_tree() DONE");
	}

	prep_search() {
		for (let [hsh, meta] of Object.entries(this.meta_obj)) {
			var line = "";
			if ( meta.hasOwnProperty('/') ) {
				line += meta['/'].join(" ").toLowerCase();
			}
			for (let [key, value] of Object.entries(meta)) {
				for (let item of String(value).toLowerCase().split(/\s+/)) {
					if (! line.includes(item)) {
						line += ' ' + item;
					}
				}
				var item = String(value);
			}
			this.search_map.set(hsh, line);
		}
		console.log(">>> prep_search() DONE");
	}

	search(txt) {
		var result_set = new Set();
		var rec = new RegExp(txt, 'iu');
		for (let [hsh, line] of this.search_map.entries()) {
			if ( rec.test(line) ) {
				result_set.add(hsh);
			}
		}
		return result_set;
	}

	hsh_to_display(hsh) {
		/*
			artist/year. album/tracknumber. title
		*/

		if ( this.meta_obj.hasOwnProperty(hsh) ) {
			return this.meta_obj[hsh]['/'].slice(-3).join(' / ');
		} else {
			return hsh;
		}

		// to be improved

		/*function pick_first(main_obj, pattern, ...arg_lst) {
			for ( let arg of arg_lst ) {
				if ( main_obj.hasOwnProperty(arg) && main_obj[arg].trim().length > 0 ) {
					return pattern.replace('<$>', main_obj[arg]);
				}
			}
			return '';
		}

		if ( obj.hasOwnProperty(hsh) ) {
			var info_obj = this.meta_obj[hsh];
			if (
				info_obj.hasOwnProperty('artist') &&
				info_obj.hasOwnProperty('album') &&
				info_obj.hasOwnProperty('title') &&
				info_obj.hasOwnProperty('tracknumber')
			) {
				return [
					pick_first(info_obj, "<?>/", "artist", "composer"),
					pick_first(info_obj, "<?>", )

			}
			
			
			var pth_lst = this.meta_obj['/'];
		} else {
			return `### ${hsh} ###`;
		}*/
	}

}
