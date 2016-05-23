from django import template
from django.conf import settings
from humanize import naturaldelta, naturaltime
from datetime import datetime


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


@register.simple_tag(takes_context=True)
def hearthstonejson(context, build=None, locale="enUS"):
	if not build:
		build = "latest"
	return settings.HEARTHSTONEJSON_URL % {"build": build, "locale": locale}
