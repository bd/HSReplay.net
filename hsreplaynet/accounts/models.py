import uuid
from django.core.urlresolvers import reverse
from django.contrib.auth.models import AbstractUser
from django.db import models


class AccountClaim(models.Model):
	id = models.UUIDField(primary_key=True)
	token = models.OneToOneField("api.AuthToken")
	created = models.DateTimeField("Created", auto_now_add=True)

	def __str__(self):
		return str(self.id)

	def save(self, *args, **kwargs):
		if not self.id:
			self.id = uuid.uuid4()
		return super().save(*args, **kwargs)

	def get_absolute_url(self):
		return reverse("account_claim", kwargs={"id": self.id})


class User(AbstractUser):
	id = models.BigAutoField(primary_key=True)
	username = models.CharField(max_length=150, unique=True)
