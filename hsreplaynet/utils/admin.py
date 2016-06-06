from django import forms
from django.contrib.admin import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.html import format_html


def set_field_admin_action(qs, field_name):
	class SetFieldForm(forms.Form):
		_selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
		field = forms.ModelChoiceField(qs, required=False)

	def set_field(self, request, queryset):
		form = None

		if "apply" in request.POST:
			form = SetFieldForm(request.POST)

			if form.is_valid():
				value = form.cleaned_data["field"]
				count = queryset.count()
				for obj in queryset:
					setattr(obj, field_name, value)
					obj.save()

				self.message_user(request, "%i changes applied." % (count))
				return HttpResponseRedirect(request.get_full_path())

		if not form:
			action = request.POST.getlist(ACTION_CHECKBOX_NAME)
			form = SetFieldForm(initial={"_selected_action": action})

		context = {"objects": queryset, "form": form, "action_name": "set_field"}
		return render(request, "admin/set_field.html", context)
	set_field.short_description = "Set %s to..." % (field_name)

	return set_field

set_user = set_field_admin_action(User.objects, "user")


def admin_urlify(column):
	def inner(obj):
		_obj = getattr(obj, column)
		if _obj is None:
			return "-"
		try:
			url = _obj.get_absolute_url()
		except AttributeError:
			url = ""
		admin_pattern = "admin:%s_%s_change" % (_obj._meta.app_label, _obj._meta.model_name)
		admin_url = reverse(admin_pattern, args=[_obj.pk])

		ret = format_html('<a href="{url}">{obj}</a>', url=admin_url, obj=_obj)
		if url:
			ret += format_html(' (<a href="{url}">View</a>)', url=url)
		return ret
	inner.short_description = column.replace("_", " ")
	return inner
