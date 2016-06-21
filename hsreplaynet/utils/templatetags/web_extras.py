from django import template
from django.conf import settings
from humanize import naturaldelta, naturaltime
from datetime import datetime
from hsreplaynet.games.models import GameReplay


register = template.Library()


@register.filter
def human_duration(value):
	return naturaldelta(value)


@register.filter
def human_time(value):
	return naturaltime(datetime.now(value.tzinfo) - value)


@register.simple_tag
def joust_static(path):
	return settings.JOUST_STATIC_URL + path


@register.simple_tag
def get_featured_game():
	id = getattr(settings, "FEATURED_GAME_ID", None)
	if not id:
		return

	try:
		replay = GameReplay.objects.get(shortid=id)
	except GameReplay.DoesNotExist:
		replay = None
	return replay


@register.simple_tag(takes_context=True)
def hearthstonejson(context, build=None, locale="enUS"):
	if not build:
		build = "latest"
	return settings.HEARTHSTONEJSON_URL % {"build": build, "locale": locale}


@register.simple_tag
def setting(name):
	return getattr(settings, name, "")
