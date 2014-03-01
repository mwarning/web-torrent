
function parseQueryParams(uri) {
    var params = {};
	var tokens;
	var re = /[?&]?([^=]+)=([^&]*)/g;
	var p = uri.indexOf("?");
	
	if(p < 0) return params;
    uri = uri.substr(p+1).replace(/\+/g, " "); 
	
    while (tokens = re.exec(uri)) {
        params[decodeURIComponent(tokens[1])] = decodeURIComponent(tokens[2]);
    }

    return params;
}

function formatSize(bytes)
{
	if(typeof bytes === "undefined") {
		return "-";
	} else if (bytes < 1024) {
		return bytes + "  b ";
	} else if (bytes < 1024*1024) {
		return (bytes/ 1024.0).toFixed(0)  + " kB";
	} else if (bytes < 1024*1024*1024) {
		return (bytes/1024.0/1024.0).toFixed(1)  + " MB";
	} else {
		return (bytes/1024.0/1024.0/1024.0).toFixed(2) + " GB";
	} 
}

/*
0 piece is not downloaded at all
1 normal priority. Download order is dependent on availability
2 higher than normal priority. Pieces are preferred over pieces with the same availability, but not over pieces with lower availability
3 pieces are as likely to be picked as partial pieces.
4 pieces are preferred over partial pieces, but not over pieces with lower availability
5 currently the same as 4
6 piece is as likely to be picked as any piece with availability 1
7 maximum priority, availability is disregarded, the piece is preferred over any other piece with lower priority
*/
function formatPriority(priority) {
	if(typeof priority === "undefined") {
		return "-";
	} else {
		return ""+priority;
	}
}

function formatProgress(final_size, current_size) {
	if(typeof final_size === "undefined" || final_size == 0) {
		return "-";
	} else if(typeof current_size === "undefined" || current_size == 0) {
		return "-";
	} else {
		return Math.round(10000.0 * current_size / final_size)/100+ "%";
	}
}

function formatValue(value) {
	if(typeof value === "undefined" ) {
		return "-";
	} else {
		return ""+value;
	}
}

function joinPath() {
  var path = "";
  for(var i=0; i<arguments.length; i++) {
	if(i > 0) {
		path += "/";
	}
	path += arguments[i];
  }
  
  var str = "";
  for(var i=0; i<path.length; i++) {
		if(i == 0) {
			str += path[i];
			continue;
		}
		
		if(str.slice(-1) == "/" && path[i] == "/") {
			continue;
		} else {
			str += path[i];
		}
  }
  return str;
}


function get(id) { return document.getElementById(id); }
function create(name) { return document.createElement(name); }
function show(e) { e.style.display='block'; }
function hide(e) { e.style.display='none'; }
function addClass(e, c) { e.classList.add(c); } //HTML5!
function removeClass(e, c) { e.classList.remove(c); }
function append(parent, tag, text) {
	var e = create(tag);
	//if(id) e.id = id;
	if(text) e.innerHTML = ""+text;
	parent.appendChild(e);
	return e;
}

function removeChilds(p) {
	while(p.hasChildNodes()) {
		p.removeChild(p.firstChild);
	}
}

function setIntervalAndExecute(fn, time) {
    fn();
	return window.setInterval(fn, time); 
}
