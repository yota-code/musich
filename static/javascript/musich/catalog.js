
class MusichCatalog {

	/* handle the catalog database */

	constructor() {
		this.meta_obj = new Object();
		this.search_map = new Map();

		this.is_loaded = false;

		this.load();
	}

	load() {
		// retrieve the meta.json(.br) file which contains
		prom_get_JSON("/get_meta").then((obj) => {
			// drop it in this.meta_obj directly
			this.meta_obj = obj;

			this.prepare();
			// confirm everything is loaded
			this.is_loaded = true;
		})
	}

	prepare() {
		for (let [hsh, meta] of Object.entries(this.meta_obj)) {
			var search = new String();
			if ( meta.hasOwnProperty('/') ) {
				search += meta['/'].toLowerCase();
			}
			for (let [key, value] of Object.entries(meta)) {
				var text = String(value).toLowerCase();
				if ( ! search.includes(text) ) {
					search += ' ' + text;
				}
			}
			this.search_map.set(hsh, search.trim());
		}
	}

	search(text) {
		var rec = new RegExp(text, 'iu');

		var result_set = new Set();
		for (let [hsh, search] of this.search_map.entries()) {
			if ( rec.test(search) ) {
				result_set.add(hsh);
			}
		}
	}

}
