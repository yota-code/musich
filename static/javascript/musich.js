

class MusichHandler {

	constructor() {

		this.queue_lst = new Array();
		this.local_lst = new Array();

		this.queue_pos = null;

		this.audio = document.getElementById("player");
		this.tracklist = this.audio.audioTracks;

		this.database = new Map();
		http_req("GET", "/get_data").then((obj) => {
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

	play_now(row) {
		if (row < 0) {
			// if row is negative, play n-th last item
			row = this.queue_lst.length - 1;
		}
		row = Math.min(row, this.queue_lst.length - 1);
		row = Math.max(row, 0);
		var key = this.queue_lst[row];
		console.log(`>>> MusichHandler.play_now(${row}) => ${key}`)
		this.audio.src = `/get_track?u=${key}`;
		this.audio.play();

		// change the queue position and refresh to reflect the change
		this.queue_pos = row;
		this.refresh_queue_lst();
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

	click_on_queue_lst(evt) {
		if (evt.target.tagName === 'TD') {
			var [col, row, key] = this.get_col_row(evt.target);
			if ( col === 3 ) { // play now !
				this.play_now(row);
			} else if ( col === 2 ) { // delete from queue
				this.queue_lst.splice(row, 1);
				if ( row == this.queue_pos ) { //  play next if current was deleted
					this.play_now(row);
				} else {
					this.refresh_queue_lst();
				}
			} else {
				if ( (col === 0) && (0 < row) ) { // move up in queue
					if ( row == this.queue_pos ) {
						this.queue_pos -= 1;
					}
					var tmp = this.queue_lst[row];
					this.queue_lst[row] = this.queue_lst[row - 1];
					this.queue_lst[row - 1] = tmp;
				} else if ( (col === 1) && (row + 1 < this.queue_lst.length) ) { // move down in queue
					if ( row == this.queue_pos ) {
						this.queue_pos += 1;
					}
					var tmp = this.queue_lst[row];
					this.queue_lst[row] = this.queue_lst[row + 1];
					this.queue_lst[row + 1] = tmp;
				}
				this.refresh_queue_lst();
			}
		}
	}

	click_on_local_lst(evt) {
		if (evt.target.tagName === 'TD') {
			var [col, row, key] = this.get_col_row(evt.target);
			console.log(`MusichHandler.click_on_local_lst(${col}, ${row}, ${key})`);
			this.queue_lst.push(key);
			if ( this.queue_lst.length === 1 || col === 0 ) { // insert into playlist and play now
				this.play_now(-1);
			} else {
				this.refresh_queue_lst();
			}
		}
	}

	click_local_play_after(key) {
		this.queue_lst.push(key);
		this.refresh_queue_lst();

		/*if (this.queue_pos === null) {
			this.queue_jump(0);
		}*/

	}

	refresh_local_lst() {
		var stack = new Array();
		for (let key of this.local_lst) {
			stack.push(`<tr><td class="local_play_now">▶️</td><td class="local_play_next">▼</td><td class="local_play_after">${key}</td></tr>`)
		}
		var h_table = document.getElementById("local_lst");
		h_table.innerHTML = stack.join('\n');
	}

	refresh_queue_lst() {

		var stack = new Array();
		for ( let i=0 ; i < this.queue_lst.length ; i++ ) {
			var line = (i === this.queue_pos) ? ` class="currently_playing"` : '';
			var key = this.queue_lst[i];
			stack.push(`<tr${line}><td class="queue_up">▲</td><td class="queue_down">▼</td><td class="queue_del">🗑</td><td class="queue_play_now">${key}</td></tr>`)
		}
		var h_table = document.getElementById("queue_lst");
		h_table.innerHTML = stack.join('\n');

	}

	search_local() {

		var txt = document.getElementById("search_input").value.trim();

		console.log(`>>> MusichHandler.search_local(${txt})`);

		if (! txt) {
			return;
		}

		var rec = new RegExp(txt, 'iu');

		var result_set = new Set();
		for (let [key, val] of this.database.entries()) {
			if ( rec.test(val) ) {
				result_set.add(key);
			}
		}
		this.local_lst = [... result_set];

		this.refresh_local_lst();

	}


}

