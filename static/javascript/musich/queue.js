
class MusichQueue {

	/*
	handle:
	 * the playing queue
	 * the play history
	 * the position of the current track
	 * the backup of them in the localStorage
	*/

	constructor() {

		this.queue_lst = new Array();
		// list of previously played songs
		this.history_lst = new Array();

		this.restore();
	}

	insert_in_queue(hsh, position) {
		this.queue_lst.splice(position, 0, hsh);
	}

	push_to_history(hsh) {
		var position = this.history_lst.indexOf(hsh);
		if ( position !== -1 ) {
			this.history_lst.splice(position, 0);
		}

		this.history_lst.unshift(hsh);
		this.history_lst = this.history_lst.slice(0, 64); // limit the history length to 64 items
	}

	cleanup(hsh_lst) {
		var res_lst = new Array();

		for (let hsh of hsh_lst) {
			if ( MUSICH_CATALOG.meta_obj.hasOwnProperty(hsh) ) {
				res_lst.push(hsh);
			}
		}

		return res_lst;
	}

	save() {
		localStorage.setItem("musichQueue", this.queue_lst);
		localStorage.setItem("musichHistory", this.history_lst);
	}

	restore() {
		var queue_lst = localStorage.getItem("musichQueue");
		if ( queue_lst !== null ) {
			this.queue_lst = this.cleanup(queue_lst);
		}

		var history_lst = localStorage.getItem("musichHistory");
		if ( history_lst !== null ) {
			this.history_lst = this.cleanup(history_lst);
		}
	}

}