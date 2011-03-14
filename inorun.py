#!/usr/bin/python
# vim: set fileencoding=utf-8 ts=2 sw=2 expandtab :

import os,sys
from optparse import OptionParser,make_option
from time import sleep
from syslog import *
from pyinotify import *

__author__ = "Benedikt Böhm, Mohammad Ebrahim Mohammadi Panah"
__copyright__ = "Copyright (c) 2007-2008 Benedikt Böhm <bb@xnull.de>, \
Copyright (c) 2011 Mohammad Ebrahim Mohammadi Panah <ebrahim@mohammadi.ir>"
__version__ = 0,1,0

OPTION_LIST = [
  make_option(
      "-c", dest = "config",
      default = "/etc/inorun/default.py",
      metavar = "FILE",
      help = "load configuration from FILE"),
  make_option(
      "-d", dest = "daemonize",
      action = "store_true",
      default = False,
      help = "daemonize inorun"),
  make_option(
      "-p", dest = "pretend",
      action = "store_true",
      default = False,
      help = "do not actually run programs"),
  make_option(
      "-v", dest = "verbose",
      action = "store_true",
      default = False,
      help = "print debugging information"),
]

DEFAULT_EVENTS = {
    "IN_CLOSE_WRITE": "/bin/true",
    "IN_CREATE":      "/bin/true",
    "IN_DELETE":      "/bin/true",
    "IN_MOVED_FROM":  "/bin/true",
    "IN_MOVED_TO":    "/bin/true"
}

class RsyncEvent(ProcessEvent):
  pretend = None

  def __init__(self, pretend=False):
    self.pretend = pretend

  def sync(self, pathname, maskname):
    args = [config.emask[maskname]]
    #if config.logfile:
    #  args.append("--log-file=%s" % config.logfile)
    #if "excludes" in dir(config):
    #  for exclude in config.excludes:
    #    args.append("--exclude=%s" % exclude)
    args.append("%s")
    args.append(config.wpath)
    args.append(pathname[len(config.wpath)+1:])
    cmd = " ".join(args)
    for node in config.rnodes:
      if self.pretend:
        syslog("would execute `%s'" % (cmd % node))
      else:
        syslog(LOG_DEBUG, "executing %s" % (cmd % node))
        proc = os.popen(cmd % node)
        for line in proc:
          syslog(LOG_DEBUG, "[inorun] %s" % line.strip())

  def process_default(self, event):
    syslog(LOG_DEBUG, "caught %s on %s" % \
        (event.maskname, os.path.join(event.path, event.name)))
    self.sync(event.pathname, event.maskname)

def daemonize():
  try:
    pid = os.fork()
  except OSError, e:
    raise Exception, "%s [%d]" % (e.strerror, e.errno)

  if (pid == 0):
    os.setsid()
    try:
      pid = os.fork()
    except OSError, e:
      raise Exception, "%s [%d]" % (e.strerror, e.errno)
    if (pid == 0):
      os.chdir('/')
      os.umask(0)
    else:
      os._exit(0)
  else:
    os._exit(0)

  os.open("/dev/null", os.O_RDWR)
  os.dup2(0, 1)
  os.dup2(0, 2)

  return 0

def load_config(filename):
  if not os.path.isfile(filename):
    raise RuntimeError, "configuration file does not exist: %s" % filename

  configdir  = os.path.dirname(filename)
  configfile = os.path.basename(filename)

  if configfile.endswith(".py"):
    configfile = configfile[0:-3]

  sys.path.append(configdir)
  exec("import %s as __config__" % configfile)
  sys.path.remove(configdir)

  global config
  config = __config__

  if not "wpath" in dir(config):
    raise RuntimeError, "no watch path given"
  if not os.path.isdir(config.wpath):
    raise RuntimeError, "watch path does not exist: %s" % config.wpath
  if not os.path.isabs(config.wpath):
    config.wpath = os.path.abspath(config.wpath)
  config.wpath = os.path.normpath(config.wpath)

  if not "rnodes" in dir(config) or len(config.rnodes) < 1:
    raise RuntimeError, "no remote nodes given"

  if not "emask" in dir(config):
    config.emask = DEFAULT_EVENTS
  for event in config.emask:
    if not event in EventsCodes.ALL_FLAGS.keys():
      raise RuntimeError, "invalid inotify event: %s" % event

  if not "edelay" in dir(config):
    config.edelay = 1
  if config.edelay < 0:
    raise RuntimeError, "event delay needs to be greater or equal to 0"

  if not "logfile" in dir(config):
    config.logfile = None

  for program in config.emask.values():
    if not os.path.isabs(program):
      raise RuntimeError, "program path needs to be absolute"
    if not os.path.isfile(program):
      raise RuntimeError, "program binary does not exist: %s" % program

  if not "initevent" in dir(config):
    config.initevent = None
  elif not config.initevent in conf.emask.keys():
    raise RuntimeError, "invalid inotify event set as initevent: %s" % event

def main():
  version = ".".join(map(str, __version__))
  parser = OptionParser(option_list=OPTION_LIST,version="inorun " + version)
  (options, args) = parser.parse_args()

  if len(args) > 0:
    parser.error("too many arguments")

  logopt = LOG_PID|LOG_CONS
  if not options.daemonize:
    logopt |= LOG_PERROR
  openlog("inorun", logopt, LOG_DAEMON)
  if options.verbose:
    setlogmask(LOG_UPTO(LOG_DEBUG))
  else:
    setlogmask(LOG_UPTO(LOG_INFO))

  load_config(options.config)

  if options.daemonize:
    daemonize()

  wm = WatchManager()
  ev = RsyncEvent(options.pretend)
  notifier = AsyncNotifier(wm, ev, read_freq=config.edelay)
  mask = reduce(lambda x,y: x|y, [EventsCodes.ALL_FLAGS[e] for e in config.emask])
  wds = wm.add_watch(config.wpath, mask, rec=True, auto_add=True)

  if config.initevent:
    syslog(LOG_DEBUG, "starting initial synchronization on %s" % config.wpath)
    ev.sync(config.wpath, config.initevent)
    syslog(LOG_DEBUG, "initial synchronization on %s done" % config.wpath)

  syslog("resuming normal operations on %s" % config.wpath)
  try:
    asyncore.loop()
  except KeyboardInterrupt:
    syslog("exiting")
  sys.exit(0)

if __name__ == "__main__":
  main()
