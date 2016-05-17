from django import template
from humanize import naturaldelta


register = template.Library()


@register.filter
def human_duration(value):
	return naturaldelta(value)
