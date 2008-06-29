//TODO 'ul#sub-tree a.link' たちに持たせているhrefプロパティのboardクエリパラメータはuri-encodeするべき
var CGI_URL = '../cgi-bin/ktkreader/ktkr.cgi';
var HTML_URL = './ktkr.html';
var current_data = [];
var current_subject = [];

var Scheduler = Class.create({
  initialize: function () {
    this.active_queue = [];
    this.expired_queue = [];
    this.running = false;
  },
  push_queue: function(x) {
    this.expired_queue.push(x);
  },
  concat_queues: function(l){
    this.expired_queue = this.expired_queue.concat(l);
  },
  run: function () {
    if (this.active_queue.length > 0) {
      (this.active_queue.shift())();
      setTimeout(this.run.bind(this),50);
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

function parse_dat_and_display(o,h) {
  var head = current_data.length + 1;
  var partitions = 100;
  //スレのdatをpartitions行ごとに分割して処理をする。
  var datl = o.responseText.split('\n').eachSlice(partitions);
  scheduler.concat_queues(datl.map(function(x,i) {
    return function() {
      $('entries-status').update('スレ描画中...');
      var l = x.map(function(line,j) {
	// DATファイルの仕様として、1行めに"スレタイ"が入っていることに注意せよ
	// DATファイルの例
	// 名無し<>sage<>2008/12/25 12:00:00 ID deadbeef<>ああああorz<>Lispを語るスレ(345)
	// 名無し<>sage<>2008/12/25 12:01:00 ID foobarrr<>1乙<>
	// </b>名無し<b><>sage<>2008/12/25 12:01:30 ID hogehoge<>1GJ!<>
	var a = line.split('<>');
	if (a.length < 5) return [DT(),DD().update(line)];
	if (a[4]) $('chrome-stream-title').down(1).update(a[4]);
	var count = head+(i*partitions)+j;
	var name = a[0].replace(/<\/b>([^<]*)<b>/g,"<b>$1</b>");
	var mail = a[1];
	var date = a[2];
	var body = a[3].replace(
	    /<a[^>]*>&gt\;&gt\;(\d{1,4})<\/a>/g,'<a class="thread-ref" href="#$1" onclick="return anchor_onclick(this);" onmouseover="anchor_onhover(this);">&gt\;&gt\;$1</a>').replace(
	    /<a[^>]*>&gt\;&gt\;(\d{1,4})-(\d{1,4})<\/a>/g,'<a class="thread-ref" href="#$1-$2" onclick="return anchor_onclick(this);" onmouseover="anchor_onhover(this);">&gt\;&gt\;$1-$2</a>');
	      return [DT().update(count + " :"+name+":"+mail+":"+date), DD().update(body)]}).compact();
      current_data = current_data.concat(l);
      l.each(function(x) {
	var dl = $('left-section').down();
	dl.appendChild(x[0]);
	dl.appendChild(x[1]);
      });
    }}));
  //完了のタスク。ツリー表示は描画をやりなおすことになっている。
  //逐次的にツリーを描画する方法はあるだろうけどまだわからん。
  scheduler.push_queue(function() {
    $('entries-status').update('完了');
    if ($('view-list1').hasClassName('tab-header-selected')) {
      show_tree();
    };
  });
  scheduler.start();
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
  var arr = current_data.map(function(x,i) {
			       var hrefs = x[1].select('a.thread-ref').map(function(x) {
									     var re = /(\d+)$/;
									     if (x.href && x.href.search(re) != -1) {
									       var p = parseInt(x.href.match(re)[1]);
									       return isNaN(p) ? null : p-1;
									     };
									     return null;
									   }).compact();
			       return (hrefs.length > 0 && hrefs.max() < i && hrefs.max())});
  //"隣接リスト"を転置する。
  var inversed_arr = arr.map(function(x,i) {return [i]});
  arr.each(function(x,i) {
	     if (x!==false) inversed_arr[x].push(i)});
  //それを木に統合する。
  var tree = tree_merge(inversed_arr);
  //DL、DT、DDタグのツリーにして表示する。
  var e = clear_dom('left-section');
  tree.each(function(x) {e.appendChild(dl_tree(x))});
}

//TODO bbsmenu.htmlが通常の"http://game13.2ch.net/netgame"のほかに、"http://pink.net/","http://pink.net/adv.html","mailto" といったリンクを含むので弾く必要がある。

//スレ一括更新
function view_thread(elm) {
  var title = $('chrome-stream-title').down(1);
  title.href = elm.href;
  title.onclick = function() {return view_thread_diff(elm)};
  $('thread-reload').onclick = function() {return view_thread_diff(elm)};
  var re = /board=(.*)&thread=(.*)/;
  if (elm.href.search(re) != -1) {
    var info = elm.href.match(re);
    new Ajax.Request(CGI_URL,{
      parameters: {board:info[1],thread:info[2]},
      onComplete: function(o,h) {
	current_data = [];
	clear_dom('left-section').appendChild(DL());
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
  var title = $('chrome-stream-title').down(0);
  title.innerHTML = elm.down(1).innerHTML;
  title.href = elm.href;
  title.onclick = function() {return view_board(elm)};
  $('viewer-refresh').onclick = function() {return view_board(elm)};
  $('chrome-stream-title').down(1).innerHTML = '';
  var re = /board=(.*)/;
  if (elm.href.search(re) != -1) {
    var board = elm.href.match(re)[1];
    new Ajax.Request(CGI_URL,{
      parameters: {board:board},
      onComplete: function(o,h) {
	current_subject = [];
	subjects(board,o.responseText);
      }});
  };
  // ブラウザが通常の動作としてリンクを開こうとするのを防ぐ
  return false;
}

function subjects(board,responseText) {
  var entries = clear_dom('entries');
  //板のsubject.txtを100行ごとに分割して処理をする。
  var subj = responseText.split('\n').eachSlice(100);
  scheduler.concat_queues(subj.map(function(lines){
    return function() {
      $('entries-status').update('板描画中...');
      lines.each(function(x) {
	var re = /(\d+).dat<>(.*)\((\d+)\)$/;
	if (x.search(re) != -1) {
	  var y = x.match(re);
	  var thread_key = y[1];
	  var thread_title = y[2];
	  var thread_rescount = y[3];
	  var re_board = /(http:\/\/[^/]+)\/(.*)/;
	  var board_host_and_path = board.search(re_board) != -1 ? board.match(re_board) : ['null','null','null'];
	  var elt = DIV({className:'entry'},
		      DIV({className:'collapsed'},
		      [DIV({className: 'entry-icons'},
		       DIV({className:'item-star star link unselectable empty'})),
		       DIV({className:'entry-date'},'(' + thread_rescount +')'),
		       DIV({className:'entry-main'},
		       [A({href:board_host_and_path[1]+"/test/read.cgi/"+board_host_and_path[2]+thread_key,
  			   target:"_blank",
			   className:"entry-original"}),
			DIV({className:'entry-secondary'},
			A({className:'entry-title',
			   href:HTML_URL+"?board="+board+"&thread="+thread_key,
			   onclick:"return view_thread(this);"},
			   thread_title))])]));
	  current_subject.push(elt);
	  entries.appendChild(elt);
	}})}}));
  scheduler.push_queue(function(){ $('entries-status').update(''); });
  scheduler.start();
}

function show_sorted_subjects(compfun) {
  var copy = current_subject.concat();
  copy.sort(compfun);
  var entries = clear_dom('entries');
  copy.each(function(x) {entries.appendChild(x)});
}

function asc_rescount(a,b){
  function f(x) {
    var re = /(\d+)/;
    var str = x.select('.entry-date')[0].innerHTML;
    if (str.search(re) != -1) {
      var parsed_i = parseInt(str.match(re)[0]);
      if (!isNaN(parsed_i)) return parsed_i;
    };
    return null;
  };
  var a_value = f(a);
  var b_value = f(b);
  if (a_value && b_value) {
    if (a_value > b_value) return -1;
    if (a_value < b_value) return 1;
    if (a_value == b_value) return 0;
  } else if (a_value) {
    return -1;
  } else if (b_value) {
    return 1;
  };
  return 0;
}

// Wiliki:Scheme:リスト処理にあったSchemeコードをそのままJavaScriptに移植したもの。
function tree_merge(relations) {
  function pick(node,trees,relations) {
    var a = relations.partition(function(r) {return (node == r[0])});
    var picked = a[0], rest = a[1];
    if (picked.length == 0) {
      var b = trees.partition(function(t) {return (node == r[0])});
      var subtree = b[0],other_trees = b[1];
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
  document.body.toggleClassName('hide-nav');
  if (document.body.hasClassName('hide-nav')) {
    $('chrome').setStyle({marginLeft: '15px;'});
  } else {
    $('chrome').setStyle({marginLeft: ''});
  }
  onresize();
}

function toggle_entries() {
  document.body.toggleClassName('hide-entries');
  onresize();
}

function toggle_folder(elt) {
  elt.toggleClassName('collapsed');
  elt.toggleClassName('expanded');
  if (elt.hasClassName('expanded')) {
    elt.down(1).src='tree-view-folder-open.gif';
  } else {
    elt.down(1).src='tree-view-folder-closed.gif';
  };
}
function clear_dom(elt) {
  var e = $(elt);
  while(e.firstChild) e.removeChild(e.firstChild);
  return e;
}

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
function anchor_onhover(elt) {
  var re = /(\d+)$/;
  var href = null;
  if (elt.href && elt.href.search(re) != -1) {
    var p = parseInt(elt.href.match(re)[1]);
    if (!isNaN(p)) href = p-1;
  };
  var e;
  if (href != null && current_data[href]) {
    e = clear_dom('quick-add-instructions');
    e.appendChild(DL([DT().update(current_data[href][0].innerHTML),
		      DD().update(current_data[href][1].innerHTML)]));
  };
  e = $('quick-add-bubble-holder');
  var pos = elt.viewportOffset();
  //150pxにはなんの根拠もない。
  pos.left+=150;
  pos.top-=150;
  e.setStyle(pos);
  if (e.hasClassName('hidden')) e.removeClassName('hidden');
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
  var w = calcSize();
  var e1 = $('chrome-footer-container'),e2 = $('viewer-box-table'), e3 = $('viewer-header');
  var f1 = $('selectors-box'),f2 = $('add-box');
  if (document.body.hasClassName('hide-entries')) {
    a.style.height = w[0]-e1.offsetHeight-e3.offsetHeight-30;
  } else {
    a.style.height = w[0]-e1.offsetHeight-e2.offsetHeight-50;
  };
  b.style.height = w[0]-f1.offsetHeight-f2.offsetHeight-50;
  c.style.height = w[0];
}

function main() {
  if (Prototype.Browser.IE) document.body.addClassName('ie6');
  Builder.dump();
  onresize();
  $('nav-toggler').onclick=toggle_nav;
  $('entries-toggler').onclick=toggle_entries;
  $('stream-prefs-menu-contents').childElements().concat([$('stream-prefs-menu')]).each(function(x) {
    x.onclick = function () {
      $('stream-prefs-menu-contents').toggleClassName('hidden')}});
  Ajax.Responders.register({
    onCreate:function() {$('entries-status').update('Ajax通信中...')},
    onComplete:function() {$('entries-status').update('Ajax通信終了')}
  });
  var e0 = $('view-cards1'),e1 = $('view-list1'),n = 'tab-header-selected';
  e0.onclick = function() {
    if (e1.hasClassName(n)) {
      e1.removeClassName(n);
      e0.addClassName(n);
      clear_dom('left-section').appendChild(DL(current_data));
    };
  };
  e1.onclick = function() {
    if (e0.hasClassName(n)) {
      e0.removeClassName(n);
      e1.addClassName(n);
      show_tree();
    };
  };
  $('order-by-newest').onclick = function(){
    show_sorted_subjects(asc_rescount);
    $('stream-prefs-menu-contents').toggleClassName('hidden')
  };
  $('order-by-oldest').onclick = function(){
    show_sorted_subjects(function(a,b) {return asc_rescount(b,a)});
    $('stream-prefs-menu-contents').toggleClassName('hidden');
  };
  //parse_bbsmenu();をktkr.htmlのロードのたび走らせるなんて冗談じゃない。
  $$('ul#sub-tree a.link.bbsmenu').each(function (x) {
    Event.observe(x,'click',function(e) {
		    view_board(x);
		    //イベント伝播を止めないと親のul.folderのonclickまで動いてしまう
		    Event.stop(e);
		    return false})});
  $('sub-tree-show-new').onclick = function() {
    $$('#sub-tree li.folder.collapsed').each(function(x) {x.onclick(x)})};
  $('sub-tree-show-all').onclick = function() {
    $$('#sub-tree li.folder.expanded').each(function(x) {x.onclick(x)})};
  $('quick-add-bubble-holder').onclick = function() {
    $('quick-add-bubble-holder').toggleClassName('hidden');
  };
  var query = window.location.search.toQueryParams();
  if (query.board) {
    var elt_a = $$('ul#sub-tree a.link.bbsmenu').detect(function(x){
      var re = /board=([^&]+)/;
      return (x.href.search(re) != -1 && x.href.match(re)[1] == query.board);
    });
    if (elt_a) {
      toggle_nav();
      //view_board(elt_a);
    };
    if (query.thread) {
      toggle_entries();
      view_thread(A({href:Object.toQueryString(query)}));
    };
  };
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
  var subtree = $('sub-tree');
  a.each(function(x) {
    var elt = LI({className:'folder unselectable collapsed',onclick:"toggle_folder(this);"},[
	       A({className:'link'},[
		 IMG({width:16,height:16,alt:"",src:"tree-view-folder-closed.gif",className:"icon icon-d-1"}),
		 SPAN({title:x.categoly,className:"name name-d-1 name-unread"},
		   SPAN({className:"name-text name-text-d-1"},x.categoly))]),
	       UL(x.boards.map(function(y){
				 return LI({className:"sub unselectable collapsed unread"},
				           A({href:y.href,className:'link bbsmenu'},
					     SPAN({title:y.name,className:"name name-d-2"},
					       SPAN({className:"name-text name-text-d-2"},y.name))));
				   }))]);
    subtree.appendChild(elt);
  });
}

window.onload = main;
window.onresize = onresize;
