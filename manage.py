#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
	sys.path.append(os.path.realpath(os.path.dirname(__file__)) + '/conf')
	os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
	
	from django.core.management import execute_from_command_line
	execute_from_command_line(sys.argv)
