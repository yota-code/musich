
// http://ccoenraets.github.io/es6-tutorial-data/promisify/


Object.defineProperty(Element.prototype, "add_text", {
	value: function(txt) {
		this.appendChild(
			document.createTextNode(txt)
		)
		return this;
	}
});

Object.defineProperty(Element.prototype, "clear", {
	value: function() {
		while (this.lastChild) {
			this.removeChild(this.lastChild);
		}
		return this;
	}
});

Object.defineProperty(Element.prototype, "grow", {
	value: function(tag, attribute_map, name_space) {
		switch ( name_space ) {
			case "html" :
				name_space = "http://www.w3.org/1999/xhtml";
				break;
			case "svg" :
				name_space = "http://www.w3.org/2000/svg";
				break;
			case "xbl" :
				name_space = "http://www.mozilla.org/xbl";
				break;
			case "xul" :
				name_space = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
				break;
		}
		
		if ( name_space !== undefined ) {
			var child = document.createElementNS(name_space, tag);
		} else {
			var child = document.createElement(tag);
		}
		
		if ( attribute_map !== undefined ) {
			for (let key in attribute_map) {
				child.setAttribute(key, attribute_map[key]);
			}
		}
		
		this.appendChild(child);
		return child;
	}
});

function http_req(method, url, headers, body) {
	return new Promise((resolve, reject) => {
		let xhr = new XMLHttpRequest();
		xhr.open(method, url);
		if (headers) {
			Object.keys(headers).forEach(key => {
				xhr.setRequestHeader(key, headers[key]);
			});
		}
		xhr.onload = () => {
			if (xhr.status >= 200 && xhr.status < 300) {
				resolve(xhr);
			} else {
				reject(xhr);
			}
		};
		xhr.onerror = () => reject(xhr);
		xhr.send(body);
	});
};

function get_json(url) {
	return http_req('GET', url).then((req) => JSON.parse(req.responseText));
}
