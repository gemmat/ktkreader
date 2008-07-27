// コード規約 eachメソッド、mapメソッドのカウンタはi,j,k...とする。for文のカウンタはs,t,u...とする。
//TODO 'ul#sub-tree a.link' たちに持たせているhrefプロパティのboardクエリパラメータはuri-encodeするべき
var CGI_URL = './ktkr.cgi';
var HTML_URL = './ktkr.html';
var current_data = [];
var current_subject = [];
var at_popup = [];

var Scheduler = Class.create({
  initialize: function () {
    this.active_queue = [];
    this.expired_queue = [];
    this.running = false;
  },
  push_queue: function(x) {
    this.expired_queue.push(x);
    this.start();
  },
  concat_queues: function(l){
    this.expired_queue = this.expired_queue.concat(l);
    this.start();
  },
  run: function () {
    if (this.active_queue.length > 0) {
      (this.active_queue.shift())();
      setTimeout(this.run.bind(this),10);
    } else {
      this.running = false;
      this.start();
    };
  },
  start: function () {
    if (!this.running && this.expired_queue.length > 0) {
      var tmp = this.active_queue;
      this.active_queue = this.expired_queue;
      this.expired_queue = tmp;
      this.running = true;
      this.run();
    };
  }
});
var scheduler = new Scheduler();

function freshObserve(element,eventName,handler){
  Event.stopObserving(element,eventName);
  return Event.observe(element,eventName,handler);
}

function parse_dat_and_display(o,h) {
  var head = current_data.length + 1;
  var partitions = 150;
  //スレのdatをpartitions行ごとに分割して処理をする。
  var datl = o.responseText.split('\n').eachSlice(partitions);
  //レスを挿入するDLタグ
  scheduler.concat_queues(datl.map(function(lines,i) {
    return function() {
      $('entries-status').innerHTML = 'スレ描画中...';
      var l = [];
      var correction = 0;
      for (var s = 0; s < lines.length; s++) {
	var line = lines[s];
	// DATファイルの仕様として、1行めに"スレタイ"が入っていることに注意せよ
	// DATファイルの例
	// 名無し<>sage<>2008/12/25 12:00:00 ID deadbeef<>ああああorz<>Lispを語るスレ(345)
	// 名無し<>sage<>2008/12/25 12:01:00 ID foobarrr<>1乙<>
	// </b>名無し<b><>sage<>2008/12/25 12:01:30 ID hogehoge<>1GJ!<>
	var a = line.split('<>');
	if (a.length < 5) {
	  correction++;
	  continue;
	};
	if (a[4]) {
	  document.title = a[4];
	  $('chrome-stream-title').down(1).innerHTML = a[4];
	};
	var count = head+(i*partitions)+s-correction;
	var name = ["<span class='res-name'>",a[0].replace(/<\/b>([^<]*)<b>/g,"<b>$1</b>"),"</span>"].join('');
	var mail = a[1];
	var date = a[2].replace(/ID:(.+)/,"<span class='res-id' onclick='id_onclick(this);'>ID:$1</span>")
	var body = a[3].replace(/<a[^>]*>&gt\;&gt\;(\d{1,4})-(\d{1,4})<\/a>/g,'<a class="thread-ref" href="#$1" onclick="return anchor_onclick(this);" onmouseover="anchor_onhover(this);">&gt\;&gt\;$1</a>-<a class="thread-ref" href="#$2" onclick="return anchor_onclick(this);" onmouseover="anchor_onhover(this);">$2</a>').replace(/<a[^>]*>&gt\;&gt\;(\d{1,4})<\/a>/g,'<a class="thread-ref" href="#$1" onclick="return anchor_onclick(this);" onmouseover="anchor_onhover(this);">&gt\;&gt\;$1</a>').replace(/(((ht|f|t)tp(s?))\:\/\/)?((([a-zA-Z0-9_\-]{2,}\.)+[a-zA-Z]{2,})|((?:(?:25[0-5]|2[0-4]\d|[01]\d\d|\d?\d)(?:(\.?\d)\.)){4}))(:[a-zA-Z0-9]+)?(\/[a-zA-Z0-9\-\._\?\,\'\/\\\+&amp;%\$#\=~]*)?/g,'<a href=$&>$&</a>').replace(/href=ttp/g,'href=http');
	var dt_dd = [DT(),DD({className:'rr'})];
	dt_dd[0].innerHTML = [count+' ',name,date].join(':');
	dt_dd[1].innerHTML = body;
	l.push(dt_dd);
      };
      current_data = current_data.concat(l);
      var frag = document.createDocumentFragment();
      for (var s = 0; s < l.length; s++) {
	frag.appendChild(l[s][0]);
	frag.appendChild(l[s][1]);
      };
      $('left-section').down().appendChild(frag);
    }}));
  //完了のタスク。ツリー表示は描画をやりなおすことになっている。
  //逐次的にツリーを描画する方法はあるだろうけどまだわからん。
  scheduler.push_queue(function() {
    $('entries-status').innerHTML = '完了';
    if ($('view-list1').hasClassName('tab-header-selected')) {
      show_tree();
    };
    if ($('view-matome').hasClassName('tab-header-selected')) {
      show_matome();
    };
  });
}

function show_tree() {
  function dl_tree(t) {
    //Convert it to a '<dl><dd><dt>...<dd><dt></dl>'.
    if (typeof t == 'number') {
      return [current_data[t][0],current_data[t][1]];
    } else {
      return DL(t.map(function(x) {return dl_tree(x)}));
    };
  };
  // アンカの関係から"隣接リスト"を作る。
  var arr = new Array(current_data.length);
  var inversed_arr = new Array(current_data.length);
  for (var s = 0; s < current_data.length; s++) {
    var hrefs = $(current_data[s][1]).select('a.thread-ref');
    var result = [];
    for (var t = 0; t < hrefs.length; t++) {
      var re = /(\d+)$/;
      var a = hrefs[t];
      if (a.href && a.href.search(re) != -1) {
	var p = parseInt(a.href.match(re)[1]);
	if (!isNaN(p)) result.push(p-1);
      };
    };
    var adj = result.length > 0 && result.max() < s && result.max();
    arr[s] = adj;
    //"隣接リスト"を転置する。
    // 親
    inversed_arr[s] = [s];
    // 子
    // 前述のresult.max() < sは必要。さもないと、親より先に子がinversed_arrにpushされ例外が発生するので注意せよ。
    if (adj !== false) inversed_arr[adj].push(s);
  };
  //それを木に統合する。
  var tree = tree_merge(inversed_arr);
  //DL、DT、DDタグのツリーにして表示する。
  $clear('left-section').appendChild(dl_tree(tree));
}

//TODO bbsmenu.htmlが通常の"http://game13.2ch.net/netgame"のほかに、"http://pink.net/","http://pink.net/adv.html","mailto" といったリンクを含むので弾く必要がある。

//スレ一括更新
function view_thread(elm) {
  var title = $('chrome-stream-title').down(1);
  title.href = elm.href;
  freshObserve(title,'click',function(e) {
    if ($(document.body).hasClassName('hide-entries')) toggle_entries();
    Event.stop(e);
    return view_thread_diff(elm);
  });
  freshObserve('thread-reload','click',function() {return view_thread_diff(elm);});
  close_popup();
  if ($(document.body).hasClassName('expand-entries')) toggle_entries_expand();
  var re = /board=(.*)&thread=(.*)/;
  if (elm.href.search(re) != -1) {
    var info = elm.href.match(re);
    new Ajax.Request(CGI_URL,{
      parameters: {board:info[1],thread:info[2]},
      onComplete: function(o,h) {
	current_data = [];
	$clear('left-section').appendChild(DL());
	parse_dat_and_display(o,h);
      }
    });
  };
  // ブラウザが通常の動作としてリンクを開こうとするのを防ぐ
  return false;
}

//スレ差分更新
function view_thread_diff(elm) {
  var re = /board=(.*)&thread=(.*)/;
  if (elm.href.search(re) != -1) {
    var info = elm.href.match(/board=(.*)&thread=(.*)/);
    new Ajax.Request(CGI_URL,{
      parameters: {board:info[1],thread:info[2],head:current_data.length},
      onComplete: parse_dat_and_display
    });
  };
  // ブラウザが通常の動作としてリンクを開こうとするのを防ぐ
  return false;
}

//スレリスト更新
function view_board(elm) {
  document.title = elm.down(1).innerHTML;
  var title = $('chrome-stream-title').down(0);
  title.innerHTML = elm.down(1).innerHTML;
  title.href = elm.href;
  freshObserve(title,'click',function(e) {
    if ($(document.body).hasClassName('hide-entries')) toggle_entries();
    Event.stop(e);
    return view_board(elm);
  });
  freshObserve('viewer-refresh','click',function() {return view_board(elm)});
  $('chrome-stream-title').down(1).innerHTML = '';
  var re = /board=(.*)/;
  if (elm.href.search(re) != -1) {
    var board = elm.href.match(re)[1];
    new Ajax.Request(CGI_URL,{
      parameters: {board:board},
      onComplete: function(o,h) {
	subjects(board,o.responseText);
      }});
  };
  // ブラウザが通常の動作としてリンクを開こうとするのを防ぐ
  return false;
}

function subjects(board,responseText) {
  var entries = $('entries');
  $('entries-status').innerHTML= '板描画中...';
  scheduler.push_queue(function() {
			 $clear('entries');
			 current_subject = [];});
  //板のsubject.txtを100行ごとに分割して処理をする。
  var subj = responseText.split('\n').eachSlice(100);
  scheduler.concat_queues(subj.map(function(lines){
    return function() {
      var frag = document.createDocumentFragment();
      for (var s = 0; s < lines.length; s++) {
	var re = /(\d+).dat<>(.*)\((\d+)\)$/;
	if (lines[s].search(re) != -1) {
	  var y = lines[s].match(re);
	  var thread_key = y[1];
	  var thread_title = y[2];
	  var thread_rescount = y[3];
	  var re_board = /(http:\/\/[^/]+)\/(.*)/;
	  var board_host_and_path = board.search(re_board) != -1 ? board.match(re_board) : ['null','null','null'];
	  var elt = DIV({className:'entry'});
	  elt.innerHTML = ['<div class="collapsed"><div class="entry-icons"><div class="item-star star link unselectable empty"></div></div><div class="entry-date">(',thread_rescount,')</div><div class="entry-main"><a class="entry-rss" target="_blank" href="http://2ch2rss.dip.jp/rss.xml?url=',encodeURI(board_host_and_path[1]+'/test/read.cgi/'+board_host_and_path[2]+thread_key),'"/><a class="entry-qrcode" target="_blank" href="http://chart.apis.google.com/chart?cht=qr&chs=150x150&choe=Shift_JIS&chl=',encodeURI('http://c.2ch.net/test/-/'+board_host_and_path[2]+thread_key+'/i'),'"/><a class="entry-original" target="_blank" href="',board_host_and_path[1],'/test/read.cgi/',board_host_and_path[2],thread_key,'"/><div class="entry-secondary"><a class="entry-title" onclick="return view_thread(this);" href="',HTML_URL,'?board=',board,'&thread=',thread_key,'">',thread_title,'</a></div></div></div></div>'].join('');
	  current_subject.push(elt);
	  frag.appendChild(elt);
	};
      };
      entries.appendChild(frag);
    }}));
  scheduler.push_queue(function(){ $('entries-status').innerHTML = ''; });
}

function show_sorted_subjects(f,asc) {
  var arr = current_subject.map(function(x,i) {return [f(x),i]});
  arr.sort(function(a,b) {
	     if (a[0] && b[0]) {
	       if (a[0] > b[0]) return -1 * asc;
	       if (a[0] < b[0]) return 1 * asc;
	       if (a[0] == b[0]) return 0;
	     } else if (a[0]) {
	       return -1 * asc;
	     } else if (b[0]) {
	       return 1 * asc;
	     };
	     return 0});
  var entries = $clear('entries');
  var frag = document.createDocumentFragment();
  for (var s = 0; s < arr.length; s++) frag.appendChild(current_subject[arr[s][1]]);
  entries.appendChild(frag);
  var e = $('stream-prefs-menu-contents');
  if (!e.hasClassName('hidden')) e.addClassName('hidden');
}

//スレッドのレス数をパースする。
function parse_entry_rescount(x) {
  var str = $(x).select('.entry-date')[0].innerHTML;
  var re = /(\d+)/;
  var parsed_rescount = false;
  if (str.search(re) != -1) parsed_rescount = parseInt(str.match(re)[1]);
  if (parsed_rescount && !isNaN(parsed_rescount)) return parsed_rescount;
  return false;
}

//スレッドのキーをパースする。
function parse_entry_unixtime(x) {
  var str = $(x).select('a.entry-title')[0].href;
  var re = /thread=(\d+)/;
  var parsed_time = false;
  if (str.search(re) != -1) parsed_time = parseInt(str.match(re)[1]);
  if (parsed_time && !isNaN(parsed_time)) return parsed_time;
  return false;
}

function calc_entry_pace(x) {
  var rescount = parse_entry_rescount(x);
  if (rescount) {
    var unixtime = parse_entry_unixtime(x);
    var d = new Date();
    if (unixtime) return rescount / ((d.getTime()/1000).toFixed() - unixtime);
  };
  return false;
}

// Wiliki:Scheme:リスト処理にあったSchemeコードをそのままJavaScriptに移植したもの。
// partitionが遅かったのでfor文にした。
function tree_merge(relations) {
  function pick(node,trees,relations) {
    var picked = [], rest = [];
    for (var s = 0; s < relations.length; s++) {
      if (node == relations[s][0])
	picked.push(relations[s]);
      else
	rest.push(relations[s]);
    };
    if (picked.length == 0) {
      var subtree = [],other_trees = [];
      for (var s = 0; s < trees.length; s++) {
	if (node == trees[s][0])
	  subtree.push(trees[s]);
	else
	  other_trees.push(trees[s]);
      };
      if (subtree.length == 0) {
	return [[node],trees,relations];
      } else {
	return [subtree[0],other_trees,relations];
      }
    } else {
      var b = merge_fold(picked[0].slice(1),[],trees,rest);
      var subtrees = b[0], trees = b[1], relations=b[2];
      subtrees.unshift(node);
      return [subtrees, trees, relations];
    }
  };
  function merge_fold(kids,subtrees,trees,relations) {
    if (kids.length == 0) {
      return [subtrees.reverse(), trees, relations];
    } else {
      var a = pick(kids[0],trees,relations);
      var subtree = a[0],trees = a[1],relations = a[2];
      subtrees.unshift(subtree);
      return merge_fold(kids.slice(1),subtrees,trees,relations);
    }
  };
  function merge(trees,relations) {
    if (relations.length == 0) {
      return trees;
    } else {
      var a = pick(relations[0][0],trees,relations);
      var subtree = a[0], trees = a[1], relations = a[2];
      trees.push(subtree);
      return merge(trees,relations);
    }
  };
  return merge([],relations);
}

function toggle_nav() {
  $(document.body).toggleClassName('hide-nav');
  onresize();
}

function toggle_entries() {
  $(document.body).toggleClassName('hide-entries');
  onresize();
}

function toggle_entries_expand() {
  if ($(document.body).hasClassName('hide-entries'))
    $(document.body).removeClassName('hide-entries');
  $(document.body).toggleClassName('expand-entries');
  onresize();
}

function toggle_folder(elt) {
  var elt = $(elt);
  elt.toggleClassName('collapsed');
  elt.toggleClassName('expanded');
  if (elt.hasClassName('expanded')) {
    elt.down(1).src='images/tree-view-folder-open.gif';
  } else {
    elt.down(1).src='images/tree-view-folder-closed.gif';
  };
}
function $clear(e) {
  var e = $(e);
  while(e.firstChild) e.removeChild(e.firstChild);
  return e;
}

//スクロールしてアンカ先のレスを表示
function anchor_onclick(elt) {
  var re = /(\d+)$/;
  var href = null;
  if (elt.href && elt.href.search(re) != -1) {
    var p = parseInt(elt.href.match(re)[1]);
    if (!isNaN(p)) href = p-1;
  };
  if (href != null && current_data[href]) {
    //これでいいのか? 16pxは根拠なし。
    $('left-section').scrollTop = current_data[href][0].offsetTop - $('left-section').offsetTop - 16;
  };
  return false;
}

//ポップアップでアンカ先のレスを表示
function anchor_onhover(elt) {
  var re = /(\d+)$/;
  var href = null;
  if (elt.href && elt.href.search(re) != -1) {
    var p = parseInt(elt.href.match(re)[1]);
    if (!isNaN(p)) href = p-1;
  };
  var e = $('quick-add-instructions-dl');
  if (href != null && current_data[href]) {
    if (at_popup.indexOf(href) == -1) {
      $('quick-add-subs').innerHTML = 'アンカ先';
      at_popup.push(href);
      //DOM要素のコピーを行う。
      e.appendChild(current_data[href][0].cloneNode(true))
      e.appendChild(current_data[href][1].cloneNode(true))
    };
  };
  e = $('quick-add-bubble-holder');
  if (e.hasClassName('hidden')) e.removeClassName('hidden');
}

//ID抽出。
function id_onclick(elt) {
  var count = 0;
  var e = $('quick-add-instructions-dl');
  var list = $$('#left-section span.res-id');
  for (var s = 0; s < list.length; s++) {
    if (list[s].innerHTML == elt.innerHTML) {
      count++;
      //DOM要素のコピーを行う。
      e.appendChild(Element.up(list[s]).cloneNode(true));
      e.appendChild(Element.next(Element.up(list[s])).cloneNode(true));
    };
  };
  $('quick-add-subs').innerHTML = elt.innerHTML + ' 抽出結果(' + count +'件)';
  e = $('quick-add-bubble-holder');
  if (e.hasClassName('hidden')) e.removeClassName('hidden');
}

function close_popup() {
  $('quick-add-instructions-dl').childElements().each(function(x) {Element.hide(x)});
  at_popup = [];
  var e = $('quick-add-bubble-holder');
  if (!e.hasClassName('hidden')) e.addClassName('hidden');
}

function calcSize() {
  var Width = 0, Height = 0;
  if( typeof( window.innerWidth ) == 'number' ) {
    //Non-IE
    Height = window.innerHeight;
    Width = window.innerWidth;
  } else if(document.documentElement &&
	    (document.documentElement.clientHeight ||
	     document.documentElement.clientWidth)) {
    //IE 6+ in 'standards compliant mode'
    Height = document.documentElement.clientHeight;
    Width = document.documentElement.clientWidth;
  } else if(document.body &&
	    (document.body.clientHeight ||
	     document.body.clientWidth)) {
    //IE 4 compatible
    Height = document.body.clientHeight;
    Width = document.body.clientWidth;
  }
  return [Height,Width];
}

function onresize() {
  var a = $('left-section');
  var b = $('sub-tree');
  var c = $('nav-toggler');
  var d = $('quick-add-bubble-holder');
  var d1 = $('quick-add-instructions-dl');
  var w = calcSize();
  var e1 = $('chrome-footer-container'),e2 = $('viewer-box-table'), e3 = $('viewer-header');
  var f1 = $('selectors-box'),f2 = $('add-box');
  var body = $(document.body);
  if (body.hasClassName('hide-nav')) {
    $('chrome').setStyle({marginLeft: '15px'});
  } else {
    $('chrome').setStyle({marginLeft: '282px'});
  }
  if (body.hasClassName('expand-entries')) {
    $('entries').style.height = Math.max(w[0]-80,0);
  } else {
    $('entries').style.height = '9em';
  };
  if (body.hasClassName('hide-entries')) {
    a.style.height = Math.max(w[0]-e1.offsetHeight-e3.offsetHeight-30,0);
  } else {
    a.style.height = Math.max(w[0]-e1.offsetHeight-e2.offsetHeight-84,0);
  };
  b.style.height = Math.max(w[0]-f1.offsetHeight-f2.offsetHeight-50,0);
  c.style.height = w[0];
  var pos = $('viewer-page-container1').viewportOffset();
  //400px,50px,480px,100pxにはなんの根拠もない。
  pos.left += 400;
  pos.top += 50;
  pos.width = Math.max(a.offsetWidth - 480,0);
  pos.height = Math.max(a.offsetHeight - 100,0);
  d.setStyle({left:pos.left + 'px',top:pos.top + 'px'});
  d1.setStyle({width:pos.width + 'px',height:pos.height + 'px'});
}

function add_bookmark(e) {
  var href = $('chrome-stream-title').down(1).href;
  var title = $('chrome-stream-title').down(1).innerHTML;
  var params = href.toQueryParams();
  if (params.board && params.thread) {
    var value = Object.toQueryString({href: href, title: title});
    var count = save2local.loadData('count') || 0;
    save2local.saveData(count,value);
    save2local.saveData('count',count + 1);
    display_bookmark();
  };
}

function delete_bookmark(e) {
  var re = /^bookmark(\d+)/;
  if (e.id.search(re) != -1) {
    var key = e.id.match(re)[1];
    save2local.saveData(key,'');
    display_bookmark();
  };
}

function display_bookmark() {
  var bookmark_count = save2local.loadData('count') || 0;
  var elt = $clear('bookmark-list')
  for (var s = 0; s < bookmark_count; s++) {
    var bookmark_value = save2local.loadData(s) || 'null';
    if (bookmark_value != 'null') {
      var params = bookmark_value.toQueryParams();
      elt.appendChild(LI({className:"sub unselectable collapsed unread"},
			 [A({id:'bookmark'+s,className:'link bookmark-delete'},
			    IMG({alt:"",src:"images/icon-unsubscribe.gif",className:"icon icon-d-1", height:"16",width:"16"})),
			  A({href:params.href,className:'link bookmark'},
			   SPAN({title:params.title,className:"name name-d-2"},
				SPAN({className:"name-text name-text-d-2"},params.title)))]));
    };
  };
  $$('ul#sub-tree a.link.bookmark-delete').each(function (x) {
    Event.observe(x,'click',function(e) {
		    delete_bookmark(x);
		    //イベント伝播を止めないと親のul.folderのonclickまで動いてしまう
		    Event.stop(e);
		    return false})});
  $$('ul#sub-tree a.link.bookmark').each(function (x) {
    Event.observe(x,'click',function(e) {
		    if (x.href) auto_pilot(x.href.toQueryParams());
		    //イベント伝播を止めないと親のul.folderのonclickまで動いてしまう
		    Event.stop(e);
		    return false})});
}

function auto_pilot(params) {
  if (params.board) {
    var bbsmenus = $$('ul#sub-tree a.link.bbsmenu');
    var re = /board=([^&]+)$/;
    for (var s = 0; s < bbsmenus.length; s++) {
      var x = bbsmenus[s];
      if (x.href.search(re) != -1 && x.href.match(re)[1] == params.board) {
	view_board(x);
	break;
      };
    };
    if (params.thread) {
      view_thread(A({href:Object.toQueryString(params)}));
    };
  };
}

function main() {
  if (Prototype.Browser.IE) $(document.body).addClassName('ie6');
  Builder.dump();
  onresize();
  Event.observe('nav-toggler','click',toggle_nav);
  Event.observe('entries-toggler','click',toggle_entries);
  Event.observe('entries-toggler2','click',toggle_entries_expand);
  Event.observe('stream-prefs-menu','click',function () {$('stream-prefs-menu-contents').toggleClassName('hidden')});
  $('stream-prefs-menu-contents').childElements().each(function(x) {
    Event.observe(x,'click',function (){$('stream-prefs-menu-contents').toggleClassName('hidden')})});
  Ajax.Responders.register({
    onCreate:function() {$('entries-status').innerHTML = 'Ajax通信中...'},
    onComplete:function() {$('entries-status').innerHTML = 'Ajax通信終了'}
  });
  var e0 = $('view-cards1'),e1 = $('view-list1'),e2 = $('view-matome'),n = 'tab-header-selected';
  Event.observe(e0,'click',function() {
    if (e1.hasClassName(n)) {
      e1.removeClassName(n);
      e0.addClassName(n);
      $clear('left-section').appendChild(DL(current_data));
      if (e2.hasClassName(n)) {
	$('left-section').insertBefore(BUTTON({className:'matome',onclick:'matome_preview();'},'プレビュー'),$('left-section').down());
	$('left-section').appendChild(BUTTON({className:'matome',onclick:'matome_preview();'},'プレビュー'));
      };
    };
  });
  Event.observe(e1,'click',function() {
    if (e0.hasClassName(n)) {
      e0.removeClassName(n);
      e1.addClassName(n);
      show_tree();
      if (e2.hasClassName(n)) {
	$('left-section').insertBefore(BUTTON({className:'matome',onclick:'matome_preview();'},'プレビュー'),$('left-section').down());
	$('left-section').appendChild(BUTTON({className:'matome',onclick:'matome_preview();'},'プレビュー'));
      };
    };
  });
  Event.observe(e2,'click',function() {
    e2.toggleClassName(n);
    if (e2.hasClassName(n)) {
      show_matome();
    } else {
      $$('#left-section .matome').each(function(x) {Element.remove(x)});
      $$('#left-section .res-delete').each(function(x) {x.removeClassName('res-delete')});
      $$('#left-section dd').each(function(dd) {
				    if (dd.hasClassName('rr')) dd.removeClassName('rr');
				    if (dd.hasClassName('r1')) dd.removeClassName('r1');
				    if (dd.hasClassName('r2')) dd.removeClassName('r2');
				    if (dd.hasClassName('r3')) dd.removeClassName('r3');
				    if (dd.hasClassName('r4')) dd.removeClassName('r4');
				    if (dd.hasClassName('aa')) dd.removeClassName('aa');
				    dd.addClassName('rr');
				  });
    };
  });
  Event.observe('order-by-newest','click',function(){show_sorted_subjects(parse_entry_rescount,1)});
  Event.observe('order-by-oldest','click',function(){show_sorted_subjects(parse_entry_rescount,-1)});
  Event.observe('stream-unsubscribe','click',function(){show_sorted_subjects(calc_entry_pace,1)});
  Event.observe('stream-rename','click',function(){show_sorted_subjects(calc_entry_pace,-1)});
  Event.observe('sub-tree-show-new','click',function() {
    scheduler.concat_queues($$('#sub-tree li.folder.collapsed').eachSlice(10).map(function(l) {
      return function(){
	for (var s = 0; s < l.length; s++) l[s].onclick(l[s])}}))});
  Event.observe('sub-tree-show-all','click',function() {
    scheduler.concat_queues($$('#sub-tree li.folder.expanded').eachSlice(10).map(function(l) {
      return function(){
	for (var s = 0; s < l.length; s++) l[s].onclick(l[s])}}))});

  Event.observe('quick-add-bubble-holder','click',close_popup);
  Event.observe('add-subs','click',add_bookmark);
  $$('ul#sub-tree a.link.bbsmenu').each(function (x) {
    Event.observe(x,'click',function(e) {
		    view_board(x);
		    //イベント伝播を止めないと親のul.folderのonclickまで動いてしまう
		    Event.stop(e);
		    return false})});
  display_bookmark();
  auto_pilot(window.location.search.toQueryParams());
}

function show_matome() {
  $$('.matome').each(function(x){Element.remove(x)});
  $('left-section').insertBefore(BUTTON({className:'matome',onclick:'matome_preview();'},'プレビュー'),$('left-section').down());
  $('left-section').appendChild(BUTTON({className:'matome',onclick:'matome_preview();'},'プレビュー'));
  $$('#left-section dt').each(function(x){
				var s = SPAN({className:'matome'});
				s.innerHTML = '<button onclick="res_toggle(this)">削除</button><button onclick="font_change(this,\'rr\')">黒</button><button onclick="font_change(this,\'r1\')\">赤</button><button onclick="font_change(this,\'r2\')">青</button><button onclick=\"font_change(this,\'r3\')\">赤小</button><button onclick="font_change(this,\'r4\')">青小</button><button onclick=\"font_change(this,\'aa\')">AA</button>';
				x.appendChild(s);
			      });
}

function matome_preview() {
  var title =  $('chrome-stream-title').down(1);
  var copy = $('left-section').cloneNode(true);
  Element.select(copy,'.res-delete').each(function(x){Element.remove(x)});
  Element.select(copy,'.matome').each(function(x){Element.remove(x)});
  Element.select(copy,'span.res-name').each(function(x) {
					      var dd = Element.up(x);
					      var elt = FONT({color:'green'});
					      elt.innerHTML = x.innerHTML;
					      dd.insertBefore(elt,x);
					      Element.remove(x);
					    });
  Element.select(copy,'span.res-id').each(function(x) {
					      var dd = Element.up(x);
					      var elt = document.createTextNode(x.innerHTML);
					      dd.insertBefore(elt,x);
					      Element.remove(x);
					    });
  Element.select(copy,'a.thread-ref').each(function(x) {
					     var dd = Element.up(x);
					     var elt = A({href:x.href});
					     elt.innerHTML = x.innerHTML;
					     dd.insertBefore(elt,x);
					     Element.remove(x);
					   });
  var str = ['<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8">',
	     '<title>'+title.innerHTML+'</title>',
	     '<style type=text/css>',
	     '.rr {color:#000000;font-size:1.0em;}',
	     '.r1 {color:#ff0000;font-size:1.2em;font-weight:bold;line-height:110%;}',
	     '.r2 {color:#0000ff;font-size:1.2em;font-weight:bold;line-height:110%;}',
	     '.r3 {color:#ff0000;font-size:1.1em;font-weight:bold;line-height:1.4;}',
	     '.r4 {color:#0000ff;font-size:1.1em;font-weight:bold;line-height:1.4;}',
	     '.aa {color:#000000;font-family:"Mona","mona-gothic-jisx0208.1990-0","ＭＳ Ｐゴシック";font-size:12px;font-size-adjust:none;font-style:normal;font-variant:normal;font-weight:normal;line-height:1em;}',
	     '</style></head><body>',
	     '<h1>'+title.innerHTML+'</h1>',
	     copy.innerHTML.replace(/ _counted="undefined"/g,'').replace(/<(DT|dt)/g,'\n<$1').replace(/<(DL|dl)/g,'\n<$1'),
	     '</body></html>'].join('\n');
  var win_doc = window.open('', '', 'menubar=yes,resizable=yes,scrollbars=yes,status=yes').document;
  win_doc.open();
  win_doc.write(str);
  win_doc.close();
}

function res_toggle(elt){
  var dt = Element.up(elt,1);
  var dd = Element.next(Element.up(elt,1));
  Element.toggleClassName(dt,'res-delete');
  Element.toggleClassName(dd,'res-delete');
}

function font_change(elt,font) {
  var dd = Element.next(Element.up(elt,1));
  if (dd.hasClassName('rr')) dd.removeClassName('rr');
  if (dd.hasClassName('r1')) dd.removeClassName('r1');
  if (dd.hasClassName('r2')) dd.removeClassName('r2');
  if (dd.hasClassName('r3')) dd.removeClassName('r3');
  if (dd.hasClassName('r4')) dd.removeClassName('r4');
  if (dd.hasClassName('aa')) dd.removeClassName('aa');
  dd.addClassName(font);
}

//bbsmenu.htmlを解析する関数。とても重い。
//bbsmenu.htmlはせいぜい1週間ごとにしか更新されないので、
//この関数をktkr.htmlのロードのたび走らせるなんて冗談じゃない。
//開発者用ユーティリティと考えてください。
//こいつの出力をktkr.htmlにハードコーディングするために使う。
function parse_bbsmenu() {
  var a = [];
  var last = null;
  $('bbsmenu_data').childElements().each(function(x) {
      if (x.tagName == 'B') {
	if (last && last.boards.length > 0) a.push(last);
        last = {categoly: x.innerHTML, boards: []};
      } else if (x.tagName == 'A' && x.href.search(/http:\/\/([^\/]+)\/([^\/]+)\/$/) != -1) {
	last.boards.push({name: x.innerHTML,href: HTML_URL + '?board=' + x.href});
      };
    });
  var subtree = $clear('sub-tree');
  var frag = document.createDocumentFragment();
  a.each(function(x) {
    var elt = LI({className:'folder unselectable collapsed',onclick:"toggle_folder(this);"},[
	       A({className:'link'},[
		 IMG({width:16,height:16,alt:"",src:"images/tree-view-folder-closed.gif",className:"icon icon-d-1"}),
		 SPAN({title:x.categoly,className:"name name-d-1 name-unread"},
		   SPAN({className:"name-text name-text-d-1"},x.categoly))]),
	       UL(x.boards.map(function(y){
				 return LI({className:"sub unselectable collapsed unread"},
				           A({href:y.href,className:'link bbsmenu'},
					     SPAN({title:y.name,className:"name name-d-2"},
					       SPAN({className:"name-text name-text-d-2"},y.name))));
				   }))]);
	   frag.appendChild(elt);
  });
  subtree.appendChild(frag);
}

Event.observe(window,'load',main);
Event.observe(window,'resize',onresize);
