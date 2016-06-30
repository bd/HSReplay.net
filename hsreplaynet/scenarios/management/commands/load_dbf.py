import os
from argparse import ArgumentTypeError
from django.core.management.base import BaseCommand
from hearthstone.dbf import Dbf
from ...models import Adventure, Scenario, Wing


def build_range(value):
	value = int(value)
	if value < 0 or value > 2**32:
		raise ArgumentTypeError("Invalid build number: %r" % (value))
	return value


class Command(BaseCommand):
	def add_arguments(self, parser):
		parser.add_argument("folder", nargs=1)
		parser.add_argument("--build", type=build_range, required=True)
		parser.add_argument("--force", action="store_true")
		parser.add_argument("--locale", default="enUS")

	def get_values(self, record, columns):
		values = {"build": self.build}
		for column in columns:
			if isinstance(column, tuple):
				column, field = column
			else:
				field = column.lower()
			value = record[column]
			if value is not None:
				if isinstance(value, dict):
					value = value[self.locale]
				values[field] = value

		return values

	def load_dbf(self, cls, dbf):
		for record in dbf.records:
			values = self.get_values(record, cls.dbf_columns)
			try:
				instance = cls.objects.get(id=record["ID"])
			except cls.DoesNotExist:
				instance = cls.objects.create(**values)
				self.stdout.write("Created %r (build %r)" % (instance, self.build))
			else:
				if self.force or instance.build < self.build:
					self.stdout.write("Updating %r to build %r" % (instance, self.build))
					for k, v in values.items():
						setattr(instance, k, v)
					instance.save()
				else:
					self.stdout.write("Skipping %r (up to date)" % (instance))

	def handle(self, *args, **options):
		dbf_folder = options["folder"][0]
		self.build = options["build"]
		self.force = options["force"]
		self.locale = options["locale"]

		classes = (Adventure, Wing, Scenario)
		for cls in classes:
			filename = os.path.join(dbf_folder, cls.dbf_filename)
			self.stdout.write("Parsing %s\n" % (filename))
			dbf = Dbf.load(filename)
			self.load_dbf(cls, dbf)
