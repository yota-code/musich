

class MusichLocal {

	constructor() {


		this.m_cur = null;
		this.last_timestamp = 0;

		this.m_hst = new Array();

		this.m_cat = new Map();
		this.load_cat();

		this.m_que = new Array();
		//this.load_que();

		this.m_hst = new Array();
		//this.load_hst();

		this.is_playing = false;

		this.refresh = setInterval(() => {
			this.update_status();
		}, 3000);

		this.update_status();


		// this.sse = new EventSource(`/_get_status?last_timestamp=${this.last_timestamp}`);
		// this.sse.onmessage = ((evt) => {
		// 	var obj = JSON.parse(evt.data);
		// 	this.update_status(obj);
		// });

		document.addEventListener("keyup", (evt) => {
			// evt.preventDefault();
			if (evt.key === "Enter") {
				var txt = evt.target.value.trim();
				this.search(txt);
			}
		}, false);

		document.getElementById("search_lst").addEventListener("click", (evt) => {
			this.click_on_search_lst(evt);
		}, false);
	
		return;

		this.database = new Map();
		
		document.getElementById("search_input").addEventListener("change", (evt) => {
			// evt.preventDefault();
			this.search_local();
		}, false);

		document.addEventListener("keyup", (evt) => {
			// evt.preventDefault();
			if (event.key === "Enter") {
				this.search_local();
			}
		}, false);

		document.getElementById("local_lst").addEventListener("click", (evt) => {
			// evt.preventDefault();
			this.click_on_local_lst(evt);
		}, false);


		document.getElementById("queue_lst").addEventListener("click", (evt) => {
			this.click_on_queue_lst(evt);
		}, false);

		document.getElementById("player").addEventListener("ended", (evt) => {
			if (this.queue_pos + 1 < this.queue_lst.length) {
				this.play_now(this.queue_pos + 1);
			}
		}, false);

	}

	switch_tab(name) {
		for (let tab of document.getElementById("tab_content").children) {
			tab.style.display = (`tab_${name}` === tab.id) ? null : "none";
		}
	}

	// load_que() {
	// 	console.log("MusichLocal.load_que()");
	// 	get_json("/_load_que").then((obj) => {
	// 		if (obj) {
	// 			this.m_que = new Array();
	// 			this.m_que = obj;
	// 			this.disp_que();
	// 		}
	// 	});
	// }

	disp_que() {
		console.log("MusichLocal.disp_que()");
		var h_ul = document.getElementById("queue_lst");
		h_ul.clear();
		for (let k of this.m_que) {
			h_ul.grow("li").add_text(k);
		}
	}

	// load_hst() {
	// 	console.log("MusichLocal.load_hst()");
	// 	get_json("/_load_hst").then((obj) => {
	// 		if (obj) {
	// 			this.m_hst = new Array();
	// 			this.m_hst = obj;
	// 			this.disp_hst();
	// 		}
	// 	});
	// }

	disp_hst(len) {
		console.log(`MusichLocal.disp_hst(${len})`);
		var h_ul = document.getElementById("history_lst");
		for (let k of this.m_hst.slice(-len)) {
			h_ul.grow("li").add_text(k);
		}
	}

	update_status() {
		console.log("this.is_playing", this.is_playing);

		get_json(`/_get_status?last_timestamp=${this.last_timestamp}`).then((obj) => {
			var h_span = document.getElementById("play_track_pth");

			if ( obj.hasOwnProperty("cur") ) {
				h_span.innerText = ( obj["cur"] === null ) ? "♫ musich ♫" : obj["cur"];
			}
			if ( obj.hasOwnProperty("que") ) {
				if ( obj["que"].length ) {
					this.m_que = obj["que"];
					this.disp_que();
				}
			}
			if ( obj.hasOwnProperty("hst") ) {
				if ( obj["hst"].length ) {
					this.m_hst = this.m_hst.concat(obj["hst"]);
					this.disp_hst(obj["hst"].length);
				}
			}
			if ( obj.hasOwnProperty("_last_") ) {
				this.last_timestamp = obj["_last_"];
			}
			if ( obj.hasOwnProperty("_play_") ) {
				this.update__play_(obj['_play_']);
			}
		});

	}



		// 	var key = obj["key"];

		// 	h_span.innerText = key;

		// 	if (this.m_que.length > 0 && key === this.m_que[0]) {

		// 		this.m_que.shift();
		// 		var h_ul = document.getElementById("queue_lst");
		// 		h_ul.firstChild.remove();

		// 		this.m_hst.push(key);
		// 		var h_ul = document.getElementById("history_lst");
		// 		h_ul.grow("li").add_text(key);
		// 	}
		// } else {
			
		// }

	load_cat() {
		console.log("MusichLocal._load_cat()");

		var h_table = document.getElementById("browse_lst");
		get_json("/_load_cat").then((obj) => {
			for ( let [key, val] of Object.entries(obj) ) {
				this.m_cat.set(key, val);
				var h_tr = h_table.grow("tr")
				h_tr.grow("td").add_text("now");
				h_tr.grow("td").add_text("next");
				h_tr.grow("td").add_text(key);
			}
			document.getElementById("search_input").disabled = false;

			// test
			this.search("test");
		});
	}

	update__play_(obj) {
		var h_input = document.getElementById("play_pause_input");
		this.is_playing = obj;

		h_input.value = (this.is_playing) ? "⏸️" : "▶️";
		h_input.disabled = false;
	}

	play_pause() {
		console.log("MusichLocal.play_pause()");

		this.is_playing = ! this.is_playing;

		var h_input = document.getElementById("play_pause_input");
		h_input.value = (this.is_playing) ? "⏸️" : "▶️";

		h_input.disabled = true;

		get_json("/play_pause").then((obj) => {
			if ( obj.hasOwnProperty("_play_") ) {
				this.update__play_(obj['_play_']);
			}
		});
	}

	search(txt) {
		console.log(`>>> MusichLocal.search(${txt})`);

		var h_table = document.getElementById("search_lst");
		if (! txt) {
			h_table.clear();
		}

		var rec = new RegExp(txt, 'iu');

		var result_set = new Set();
		for (let [key, val] of this.m_cat.entries()) {
			if ( rec.test(key) || rec.test(val) ) {
				result_set.add(key);
			}
		}
		var result_lst = [... result_set];

		for (let key of result_lst) {
			var h_tr = h_table.grow("tr")
			h_tr.grow("td").add_text("now");
			h_tr.grow("td").add_text("next");
			h_tr.grow("td").add_text(key);
		}
	}

	click_on_search_lst(evt) {
		if (evt.target.tagName === 'TD') {
			var [col, row, what] = this.get_col_row(evt.target);
			console.log(`MusicLocal.click_on_search_lst(${col}, ${row}, ${what})`);
			var when = ["now", "next", "after"][col];
			http_req("POST", "./update_queue", {"Content-Type": "application/json"}, JSON.stringify([when, what])).then((obj) => {
				console.log(obj);



			})

			return;
			this.queue_lst.push(key);
			if ( this.queue_lst.length === 1 || col === 0 ) { // insert into playlist and play now
				this.play_now(-1);
			} else {
				this.refresh_queue_lst();
			}
		}
	}

	get_col_row(elem) {
		var h_td = elem;
		var h_tr = h_td.parentNode;
		var col  = Array.prototype.indexOf.call(h_tr.children, h_td);
		var h_table = h_tr.parentNode;
		var row  = Array.prototype.indexOf.call(h_table.children, h_tr);
		var key = h_tr.lastChild.innerText;
		return [col, row, key];
	}


}

/*
.then((obj) => {
			for (let line of obj.split('\n')) {
				var [key, val] = line.split('\t', 2);
				this.database.set(
					key,
					line.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
				);
			}
			document.getElementById("search_input").disabled = false;
			this.search_local();
		})
*/