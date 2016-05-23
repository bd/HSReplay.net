from django.core.urlresolvers import reverse
from django.db import models
from hsreplaynet.utils import generate_key


class AccountClaim(models.Model):
	id = models.CharField(max_length=40, primary_key=True)
	token = models.OneToOneField("api.AuthToken")
	created = models.DateTimeField("Created", auto_now_add=True)

	def save(self, *args, **kwargs):
		if not self.id:
			self.id = generate_key()
		return super().save(*args, **kwargs)

	def __str__(self):
		return self.id

	def get_absolute_url(self):
		return reverse("account_claim", kwargs={"id": self.id})
