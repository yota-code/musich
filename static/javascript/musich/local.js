/*
	this.sse = new EventSource(`/_get_status?last_timestamp=${this.last_timestamp}`);
	this.sse.onmessage = ((evt) => {
		var obj = JSON.parse(evt.data);
		this.request_status(obj);
	});
*/

class MusichLocal {

	constructor() {

		this.clock = new Date();
		this.zero = this.clock.getTime();
		this.start = 0;

		this.m_cat = new MusichCatalog();
		this.m_cat.load().then(() => {
			this.update_stack();
			this.switch_tab('queue');
			document.getElementById("search_input").disabled = false;
		});

		this.is_playing = false;

		/* this.refresh = setInterval(() => {
			this.update_stack();
		}, 5000); disabled for debug */

		this.progress = setInterval(() => {
			this.update_status();
		}, 1000); 

		this.prev_search = null;
		var h_hinput = document.getElementById("search_input");
		h_hinput.addEventListener("keyup", (evt) => {
			evt.preventDefault();
			var txt = evt.target.value.trim();
			console.log(evt, txt);
			if ( txt.length > 3 && this.prev_search !== txt ) {
				this.search(txt);
				this.prev_search = txt;
			}
		}, false);
	
		return;
	}

	update_status() {
		// TODO: entretenir le temps passé sans faire un refresh aussi fréquent ?
		prom_get_JSON(`_get_status`).then((obj) => {

			var h_span = document.getElementById("play_track_pth");
			var h_range = document.getElementById("play_range_input");
			var h_pause = document.getElementById("play_pause_input");

			if ( obj[0] === null ) {
				h_span.textContent = "♫ musich ♫";
				h_range.value = 0;
				h_range.max = 100;
				h_pause.value = "▶️";
			} else {
				h_span.textContent = this.m_cat.hsh_to_display(obj[0]);
				h_range.value = obj[1];
				h_range.max = obj[2];
				h_pause.value = (obj[3]) ? "⏸️" : "▶️";
			}

			h_pause.disabled = false;
		});
	}

	update_stack() {
		prom_get_JSON('_get_stack?&p=true&n=true').then((obj) => {
			this.refresh_stack(obj);
		});
	}

	refresh_stack(obj) {
		/* obj could contains either next or prev or both */
		for ( let [key, value] of Object.entries(obj) ) {
			var h_table = document.getElementById(`${key}_lst`);
			h_table.clear();
			for ( let hsh of value ) {
				var h_tr = h_table.grow('tr');
				var m_meta = this.m_cat.meta_obj[hsh];
				h_tr.grow('td').add_text(this.m_cat.hsh_to_display(hsh));
			}
		}
	}

	set_position(value) {
		console.log("set position", value);
		prom_get(`_set_position?&t=${value}`);
	}

	switch_tab(name) {
		for (let h_button of document.getElementById("tab_select").children) {
			h_button.style.backgroundColor = (`tab_select_${name}` === h_button.id) ? "lightblue" : "white";
		}
		for (let h_div of document.getElementById("tab_content").children) {
			h_div.style.display = (`tab_content_${name}` === h_div.id) ? null : "none";
		}
	}

	search(txt) {
		console.log(`>>> MusichLocal.search(${txt})`);

		var result_set = this.m_cat.search(txt);

		var h_table = document.getElementById("search_lst");
		h_table.clear();

		for ( let hsh of result_set ) {
			var h_tr = h_table.grow('tr');
			var h_td = h_tr.grow('td').add_text(this.m_cat.hsh_to_display(hsh));
			h_td.onclick = ((evt) => { this.push_to_queue(hsh); });
		}
	}

	push_to_queue(hsh) {
		prom_get_JSON(`_push_to_queue?&h=${hsh}`).then((obj) => {
			this.refresh_stack(obj);
		});
	}

	/*update_status(obj) {
		console.log(`MusichLocal.update_status(${JSON.stringify(obj)})`);
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
			this.is_playing = obj['_play_'];
		}

		if ( obj.hasOwnProperty("_pos_") ) {
			var [position, duration] = obj['_pos_'];
			var h_input = document.getElementById("play_range_input");
			h_input.value = 100.0 * position / duration;
		}

		var h_input = document.getElementById("play_pause_input");

		h_input.value = (this.is_playing) ? "⏸️" : "▶️";
		h_input.disabled = false;
	}*/

	play_pause() {
		console.log("MusichLocal.play_pause()");

		var h_input = document.getElementById("play_pause_input");
		h_input.disabled = true;

		prom_get("_play_pause").then((obj) => {
			console.log(obj);
			h_input.value = (obj) ? "⏸️" : "▶️";
			h_input.disabled = false;

		});
	}

	play_next() {
		console.log("MusichLocal.play_next()");
		prom_get_JSON("_play_next").then((obj) => {
			this.refresh_stack(obj);
		});
	}


	click_on_search_lst(evt) {
		if (evt.target.tagName === 'TD') {
			var [col, row, what] = this.get_col_row(evt.target);
			console.log(`MusicLocal.click_on_search_lst(${col}, ${row}, ${what})`);
			var when = ["now", "next", "after"][col];
			http_req("POST", "./update_queue", {"Content-Type": "application/json"}, JSON.stringify([when, what])).then((obj) => {
				console.log(obj);
				this.update_status(obj);
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
