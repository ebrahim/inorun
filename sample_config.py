# directory that should be watched for changes
wpath = "/var/www/"

# exclude list for rsync
rexcludes = [
	"/localhost",
]

# common remote path
rpath = "/var/www/"

# remote locations in rsync syntax
rnodes = [
	"a.mirror.com:" + rpath,
	"b.mirror.com:" + rpath,
	"c.mirror.com:" + rpath,
]

# limit remote sync speed (in KB/s, 0 = no limit)
#rspeed = 0

# event mask (only sync on these events)
#emask = [
#	"IN_CLOSE_WRITE",
#	"IN_CREATE",
#	"IN_DELETE",
#	"IN_MOVED_FROM",
#	"IN_MOVED_TO",
#]

# event delay in seconds (prevents huge amounts of syncs, but dicreases the
# realtime side of things)
#edelay = 10

# rsync log file for updates
#logfile = /var/log/inosync.log

# rsync binary path
#rsync = "/usr/bin/rsync"
