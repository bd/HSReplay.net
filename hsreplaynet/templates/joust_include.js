{% load static from staticfiles %}
{% load web_extras %}

var joust_required = [
	"{% joust_static 'joust.css' %}",
	"https://cdnjs.cloudflare.com/ajax/libs/react/15.1.0/react.min.js",
	"https://cdnjs.cloudflare.com/ajax/libs/react/15.1.0/react-dom.min.js",
	"{% joust_static 'joust.js' %}",
	"{% static 'web/joust-extra.js' %}"
];

$(document).ready(function() {
	$('#joust-lightbox').click(function(e) {
		e.preventDefault();
		$('#joust-lightbox').hide();
	}).children().click(function(e) {
	  return false;
	});
	var joust_started = false;
	var joust_check = function() {
		if(joust_required.length) {
			var file = joust_required.shift();
			var tag = file.match(/\.css$/) ? 'link' : 'script';
			var element = document.createElement(tag);
			element.onload = function() {
				joust_check();
			};
			if(tag == 'link') {
				element.href = file;
				element.rel = 'stylesheet';
			}
			else {
				element.src = file;
			}
			document.getElementsByTagName('head')[0].appendChild(element);
		}
		else if(!joust_started) {
			joust_started = true;

			var shim = document.createElement('style');
			shim.innerText = "{% filter escapejs %}{% include 'games/svg-paths-shim.css' with svg='/static/web/svg-paths.svg' %}{% endfilter %}";
			document.getElementsByTagName('head')[0].appendChild(shim);

			JoustExtra.setup({
				hearthstonejson: "{% setting 'HEARTHSTONEJSON_URL' %}"
			});
			Joust.viewer("joust-promo-container")
				.metadata(JoustExtra.metadata)
				.assets("{% joust_static 'assets/' %}")
				.cardArt("{% joust_static 'card-art/' %}")
				.width("100%")
				.height("100%")
				.fromUrl("{{ featured_game.replay_xml.url|safe }}");
		}
	};
	$('#feat-joust-screenshot').click(function(e) {
		e.preventDefault();
		$('#joust-lightbox').fadeIn();
		joust_check();
	});
});

