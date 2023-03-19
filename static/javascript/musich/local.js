/*
	this.sse = new EventSource(`/_get_status?last_timestamp=${this.last_timestamp}`);
	this.sse.onmessage = ((evt) => {
		var obj = JSON.parse(evt.data);
		this.request_status(obj);
	});
*/

class MusichLocal {

	constructor() {

		this.play_start = 0 ;
		this.play_stop = 0 ;
		this.play_status = null;
		this.play_position = 0;

		this.version = {
			'prev': -1,
			'next': -1
		};

		this.m_cat = new MusichCatalog();
		this.m_cat.load().then(() => {
			this.fetch();
			this.switch_tab('queue');
			document.getElementById("search_input").disabled = false;
		});


		setInterval(() => {
			this.fetch();
		}, 5000);

		var h_range = document.getElementById("play_range_input");
		setInterval(() => {
			if ( this.play_status == true ) {
				this.play_position = (this.play_start == 0) ? (0) : (Date.now() - this.play_start);
				h_range.value = this.play_position;
			}
		}, 250);

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
	}

	fetch() {
		prom_get_JSON(`_get_info?&n=${this.version['next']}&p=${this.version['prev']}`).then((obj) => {
			this.refresh(obj);			
		});
	}

	refresh(obj) {
		/* refresh:
			- the tab [queue], if the key 'next' is present
			- the tab [history], if the key 'prev' is present
			- the player information, if the key 'play' is present, whose fields are :
				- the hsh of the track loaded (playing or paused), or null if none
				- the position in the track
				- the duration of the track
				- the status with convention null for STOPPED, false for PAUSED, true for PLAYING
		*/

		console.log(obj);

		if ( obj.hasOwnProperty('track') ) {
			let [hsh, pos, dur, pps] = obj['track'];

			var h_span = document.getElementById("play_track_pth");
			var h_range = document.getElementById("play_range_input");
			var h_pause = document.getElementById("play_pause_input");

			if ( hsh === null ) {
				h_span.textContent = "♫ musich ♫";
				this.play_start = 0;
				this.play_position = 0;
				h_range.value = 0;
				h_range.max = 100;
				h_pause.value = "▶️";
				h_pause.disabled = true;
			} else {
				h_span.textContent = this.m_cat.hsh_to_display(hsh);
				if ( pos !== null ) {
					this.play_start = Date.now() - pos;
					this.play_position = pos;
				}
				h_range.max = dur;
				h_pause.value = (pps) ? "⏸️" : "▶️";
				h_pause.disabled = false;
			}

			this.play_status = pps;
			h_range.value = this.play_position;
		}

		for ( let key  of ['prev', 'next'] ) {
			if ( obj.hasOwnProperty(key) ) {
				var h_table = document.getElementById(`${key}_lst`);
				h_table.clear();
				var n=0;
				for ( let hsh of obj[key][1]) {
					var h_tr = h_table.grow('tr', {
						'onclick': (key === 'prev') ?
						`musich.push_to_queue("${hsh}")` :
						`musich.pull_from_queue("${hsh}", ${n})`
					});
					var m_meta = this.m_cat.meta_obj[hsh];
					h_tr.grow('td').add_text(this.m_cat.hsh_to_display(hsh));
					n += 1;
				}
				this.version[key] = obj[key][0];
			}
		}
	}

	push_to_queue(hsh) {
		console.log(`MusichLocal.push_to_queue(${hsh})`);
		prom_get_JSON(`_push_to_queue?&h=${hsh}`).then((obj) => {
			this.refresh(obj);
		});
	}

	pull_from_queue(hsh, index) {
		console.log(`MusichLocal.pull_from_queue(${hsh}, ${index})`);
		prom_get_JSON(`_pull_from_queue?&h=${hsh}&i=${index}`).then((obj) => {
			this.refresh(obj);
		});
	}

	jump_to(pos) {
		var h_range = document.getElementById("play_range_input");
		this.play_start = this.play_start + ( pos - this.play_position );
		this.play_position = pos;
		h_range.value = this.play_position;

		prom_get_JSON(`_set_position?&t=${pos}`).then((obj) => {
			this.refresh(obj);
		});
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
			var h_tr = h_table.grow('tr', {'onclick' : `musich.push_to_queue("${hsh}")`});
			var h_td = h_tr.grow('td').add_text(this.m_cat.hsh_to_display(hsh));
		}
	}

	play_pause() {
		console.log("MusichLocal.play_pause()");

		/* as soon as the button is clicked, some default action are taken waiting for the answer from the server */
		var h_input = document.getElementById("play_pause_input");
		h_input.disabled = true;

		if ( this.play_status !== null ) {
			this.play_status = !(this.play_status);
		}
		
		prom_get("_play_pause").then((obj) => {
			this.refresh(obj);
		});
	}

	play_next() {
		console.log("MusichLocal.play_next()");
		prom_get_JSON("_play_next").then((obj) => {
			this.refresh(obj);
		});
	}


	/*click_on_search_lst(evt) {
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
	}*/

	/*get_col_row(elem) {
		var h_td = elem;
		var h_tr = h_td.parentNode;
		var col  = Array.prototype.indexOf.call(h_tr.children, h_td);
		var h_table = h_tr.parentNode;
		var row  = Array.prototype.indexOf.call(h_table.children, h_tr);
		var key = h_tr.lastChild.innerText;
		return [col, row, key];
	}*/


}
