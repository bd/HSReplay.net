from django import template
from humanize import naturaldelta, naturaltime
from datetime import datetime


register = template.Library()


@register.filter
def human_duration(value):
	return naturaldelta(value)

@register.filter
def human_time(value):
	return naturaltime(datetime.now(value.tzinfo) - value)
