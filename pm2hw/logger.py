import sys
import logging
from typing import Sequence, Set
from logging import NOTSET, DEBUG, INFO, WARN, WARNING, ERROR, CRITICAL, LogRecord

from . import __name__ as logger_name

PROTOCOL = 5
VERBOSE = INFO - 1

LOG = "INFO.LOG"
PROGRESS = "INFO.PROGRESS"
EXCEPTION = "ERROR.EXCEPTION"
FATAL = "CRITICAL.FATAL"

_levelToName = {
	PROTOCOL: "PROTOCOL",
	VERBOSE: "VERBOSE",
	**logging._levelToName
}

logger = logging.getLogger(logger_name)

class SubtypedMessage:
	def __init__(self, msg: str, subtype: str):
		self._msg = msg
		self._subtype = subtype.upper()

	@property
	def subtype(self):
		return self._subtype

	def __str__(self):
		return str(self._msg)

class Formatter(logging.Formatter):
	default_time_format = "%H:%M:%S"
	default_msec_format = "%s.%03d"
	default_shortlevelname = {
		f"{INFO}.LOG": "   ",
		f"{INFO}.PROGRESS": "   ",
	}
	default_shortlevelname_format = "{0[0]}: "

	def __init__(self, fmt=None, datefmt=None, style="{", validate=True) -> None:
		super().__init__(fmt, datefmt, style, validate)

	def format(self, record: LogRecord):
		if isinstance(record.msg, SubtypedMessage):
			levelname = record.msg.subtype
			lookup = f"{record.levelno}.{levelname}"
		else:
			levelname = record.levelname
			lookup = str(record.levelno)
		record.shortlevelname = self.default_shortlevelname.get(
			lookup,
			self.default_shortlevelname_format.format(levelname)
		)
		return super().format(record)

class Handler(logging.Handler):
	def __init__(self, level, *, handler=None, raw_handler=None) -> None:
		super().__init__(level)
		self._handler = raw_handler or handler or (lambda r: None)
		self._raw = bool(raw_handler)

	def set_handler(self, handler):
		self._handler = handler

	def emit(self, record):
		self._handler(record if self._raw else self.format(record))

	def add_subtype_filter(self, level: int, allow: Sequence[str] = (), reject: Sequence[str] = ()):
		def filterer(record: LogRecord):
			if record.levelno == level:
				subtype = record.msg.subtype if isinstance(record.msg, SubtypedMessage) else ""
				if allow:
					return subtype in allow
				if reject:
					return subtype not in reject
			return True
		self.addFilter(filterer)

class PiecewiseFilter(logging.Filter):
	def __init__(self, name):
		super().__init__(name)
		self.enabled: Set[str] = set()
		self.all_enabled = True

	def filter(self, record: LogRecord):
		if not super().filter(record):
			# Name check failed
			return False
		return self.all_enabled or (
			f"{record.levelname}.{record.msg.subtype}"
			if isinstance(record.msg, SubtypedMessage) else
			record.levelname
		) in self.enabled

	def enable(self, *args):
		what = {_levelToName.get(a, str(a)).upper() for a in args}
		if "ALL" in what:
			self.all_enabled = False
			what.remove("ALL")
		self.enabled.update(what)

	def disable(self, *args: str):
		for a in args:
			x = _levelToName.get(a, str(a)).upper()
			if x == "ALL":
				self.enabled.clear()
				return
			self.enabled.remove(x)

logger_filter = PiecewiseFilter(logger_name)
logger.addFilter(logger_filter)
enable = logger_filter.enable
disable = logger_filter.disable

nice_formatter = Formatter("[{asctime}] {shortlevelname}{message}")

def add_log_only_handler():
	handler = Handler(logging.INFO)
	handler.setFormatter(nice_formatter)
	handler.addFilter(lambda record: record.levelno == logging.INFO)
	logger.addHandler(handler)
	return handler

def protocol(msg, data=None, **kwargs):
	if data:
		msg = " ".join(msg, *(f"{b:02x}" for b in data))
	else:
		msg = msg.format(**kwargs)
	logger.log(PROTOCOL, msg)

def debug(msg, **kwargs):
	logger.debug(msg.format(**kwargs))

def verbose(msg, **kwargs):
	logger.log(VERBOSE, msg.format(**kwargs))

def info(msg, **kwargs):
	logger.info(msg.format(**kwargs))

def log(msg, **kwargs):
	logger.info(SubtypedMessage(msg.format(**kwargs), "LOG"))

class progress(SubtypedMessage):
	def __init__(self, msg: str, end: int, **kwargs):
		super().__init__(msg, "PROGRESS")
		self.msg = msg
		self.current = 0
		self.percent = 0
		self.end = end
		self.kwargs = kwargs
		logger.info(self)

	def update(self, value: int):
		self.current = value
		self.percent = value / self.end
		logger.info(self)

	def __str__(self):
		return self.msg.format(**{
			"cur": self.current,
			"%": self.percent,
			"end": self.end,
		}, **self.kwargs)

def warn(msg, **kwargs):
	logger.warn(msg.format(**kwargs))

warning = warn

def error(msg, **kwargs):
	logger.error(msg.format(**kwargs))

def critical(msg, **kwargs):
	logger.critical(msg.format(**kwargs))

def fatal(msg, **kwargs):
	logger.fatal(SubtypedMessage(msg.format(**kwargs), "FATAL"))

def exception(msg, exc_info=True, **kwargs):
	logger.exception(SubtypedMessage(msg.format(**kwargs), "EXCEPTION"), exc_info=exc_info)
