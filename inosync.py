#!/usr/bin/python
# vim: set fileencoding=utf-8 ts=2 sw=2 expandtab :

import os,sys
from optparse import OptionParser,make_option
from time import sleep
from syslog import *
from pyinotify import *

__author__ = "Benedikt Böhm"
__copyright__ = "Copyright (c) 2007-2008 Benedikt Böhm <bb@xnull.de>"
__version__ = 0,2,2

OPTION_LIST = [
  make_option(
      "-c", dest = "config",
      default = "/etc/inosync/default.py",
      metavar = "FILE",
      help = "load configuration from FILE"),
  make_option(
      "-d", dest = "daemonize",
      action = "store_true",
      default = False,
      help = "daemonize %prog"),
  make_option(
      "-p", dest = "pretend",
      action = "store_true",
      default = False,
      help = "do not actually call rsync"),
  make_option(
      "-v", dest = "verbose",
      action = "store_true",
      default = False,
      help = "print debugging information"),
]

DEFAULT_EVENTS = [
    "IN_CLOSE_WRITE",
    "IN_CREATE",
    "IN_DELETE",
    "IN_MOVED_FROM",
    "IN_MOVED_TO"
]

class RsyncEvent(ProcessEvent):
  pretend = None

  def __init__(self, pretend=False):
    self.pretend = pretend

  def sync(self):
    args = [config.rsync, "-ltrp", "--delete"]
    args.append("--bwlimit=%s" % config.rspeed)
    if config.logfile:
      args.append("--log-file=%s" % config.logfile)
    if "excludes" in dir(config):
      for exclude in config.excludes:
        args.append("--exclude=%s" % exclude)
    args.append(config.wpath)
    args.append("%s")
    cmd = " ".join(args)
    for node in config.rnodes:
      if self.pretend:
        syslog("would execute `%s'" % (cmd % node))
      else:
        syslog(LOG_DEBUG, "executing %s" % (cmd % node))
        proc = os.popen(cmd % node)
        for line in proc:
          syslog(LOG_DEBUG, "[rsync] %s" % line.strip())

  def process_default(self, event):
    syslog(LOG_DEBUG, "caught %s on %s" % \
        (event.maskname, os.path.join(event.path, event.name)))
    self.sync()

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

  if not "rnodes" in dir(config) or len(config.rnodes) < 1:
    raise RuntimeError, "no remote nodes given"

  if not "rspeed" in dir(config) or config.rspeed < 0:
    config.rspeed = 0

  if not "emask" in dir(config):
    config.emask = DEFAULT_EVENTS
  for event in config.emask:
    if not event in EventsCodes.ALL_FLAGS.keys():
      raise RuntimeError, "invalid inotify event: %s" % event

  if not "edelay" in dir(config):
    config.edelay = 10
  if config.edelay < 0:
    raise RuntimeError, "event delay needs to be greater or equal to 0"

  if not "logfile" in dir(config):
    config.logfile = None

  if not "rsync" in dir(config):
    config.rsync = "/usr/bin/rsync"
  if not os.path.isabs(config.rsync):
    raise RuntimeError, "rsync path needs to be absolute"
  if not os.path.isfile(config.rsync):
    raise RuntimeError, "rsync binary does not exist: %s" % config.rsync

def main():
  version = ".".join(map(str, __version__))
  parser = OptionParser(option_list=OPTION_LIST,version="%prog " + version)
  (options, args) = parser.parse_args()

  if len(args) > 0:
    parser.error("too many arguments")

  logopt = LOG_PID|LOG_CONS
  if not options.daemonize:
    logopt |= LOG_PERROR
  openlog("inosync", logopt, LOG_DAEMON)
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

  syslog(LOG_DEBUG, "starting initial synchronization on %s" % config.wpath)
  ev.sync()
  syslog(LOG_DEBUG, "initial synchronization on %s done" % config.wpath)

  syslog("resuming normal operations on %s" % config.wpath)
  asyncore.loop()
  sys.exit(0)

if __name__ == "__main__":
  main()
