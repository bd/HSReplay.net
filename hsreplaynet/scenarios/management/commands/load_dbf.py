import os
from argparse import ArgumentTypeError
from collections import OrderedDict
from django.core.management.base import BaseCommand
from hearthstone.dbf import Dbf
from ...models import Adventure, Scenario, Wing


def build_range(value):
	value = int(value)
	if value < 0 or value > 2**32:
		raise ArgumentTypeError("Invalid build number: %r" % (value))
	return value


class Command(BaseCommand):
	tables = OrderedDict([
		("ADVENTURE", Adventure),
		("WING", Wing),
		("SCENARIO", Scenario),
	])

	def add_arguments(self, parser):
		parser.add_argument("path", nargs=1)
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

	def load_dbf(self, filename):
		self.stdout.write("Parsing %s" % (filename))
		dbf = Dbf.load(filename)
		if dbf.name not in self.tables:
			self.stderr.write("No handler for %r (%r)" % (filename, dbf.name))
			return

		cls = self.tables[dbf.name]
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

	def load_dbf_folder(self, path):
		for dbf_name in self.tables:
			filename = os.path.join(path, dbf_name + ".xml")
			self.load_dbf(filename)

	def handle(self, *args, **options):
		path = options["path"][0]
		self.build = options["build"]
		self.force = options["force"]
		self.locale = options["locale"]

		if os.path.isdir(path):
			self.load_dbf_folder(path)
		else:
			self.load_dbf(path)
