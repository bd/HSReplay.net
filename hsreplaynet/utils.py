import time
from django.core.urlresolvers import reverse


_module_load_start = time.clock()


def admin_urlify(column):
	def inner(obj):
		_obj = getattr(obj, column)
		try:
			url = _obj.get_absolute_url()
		except AttributeError:
			url = ""
		admin_pattern = "admin:%s_%s_change" % (_obj._meta.app_label, _obj._meta.model_name)
		admin_url = reverse(admin_pattern, args=[_obj.pk])
		ret = '<a href="%s">%s</a>' % (admin_url, _obj)
		if url:
			ret += ' (<a href="%s">View</a>)' % (url)
		return ret
	inner.allow_tags = True
	inner.short_description = column.replace("_", " ")
	return inner


def _time_elapsed():
	return time.clock() - _module_load_start
