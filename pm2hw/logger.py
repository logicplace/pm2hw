# TODO: import logging
import sys

WARN_ENABLED = False
DEBUG_ENABLED = False
VERBOSE_ENABLED = False
PROTOCOL_ENABLED = False

def localizer(fun):
	def handler(msg, *args, **kwargs):
		# TODO: localize
		formatted = msg.format(*args, **kwargs)
		fun(formatted)
	
	return handler

@localizer
def log(msg):
	print(msg)

@localizer
def protocol(msg):
	if PROTOCOL_ENABLED:
		print(msg)

def protocol_data(direction, data):
	if PROTOCOL_ENABLED:
		if data:
			print(direction, *("{:02x}".format(b) for b in data))

@localizer
def verbose(msg):
	if VERBOSE_ENABLED:
		print(msg)

@localizer
def warn(msg):
	if WARN_ENABLED:
		print(msg)

@localizer
def debug(msg):
	if DEBUG_ENABLED:
		print(msg)

@localizer
def error(msg):
	print(msg, file=sys.stderr)


def set(*args: str, enabled: bool):
	global WARN_ENABLED, DEBUG_ENABLED, VERBOSE_ENABLED, PROTOCOL_ENABLED
	what = {str(a).lower() for a in args}

	if "warn" in what:
		WARN_ENABLED = enabled
	if "debug" in what:
		DEBUG_ENABLED = enabled
	if "verbose" in what:
		VERBOSE_ENABLED = enabled
	if "protocol" in what:
		PROTOCOL_ENABLED = enabled

def enable(*args):
	set(*args, enabled=True)

def disable(*args):
	set(*args, enabled=False)
