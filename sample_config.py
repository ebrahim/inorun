# directory that should be watched for changes
wpath = "/repo/ubuntu"

## Not implemented yet:
# exclude list for rsync
#rexcludes = [
#	"/localhost",
#]

rnodes = [ "10.0.0.2" ]

# event mask (only sync on these events)
emask = {
	"IN_CLOSE_WRITE": "/usr/local/bin/sync-copy",
	"IN_CREATE":      "/usr/local/bin/sync-copy",
	"IN_MOVED_TO":    "/usr/local/bin/sync-copy",
	"IN_DELETE":      "/usr/local/bin/sync-remove",
	"IN_MOVED_FROM":  "/usr/local/bin/sync-remove",
}

# event delay in seconds (prevents huge amounts of syncs, but dicreases the
# realtime side of things)
# Default: 1
#edelay = 10

## Not implemented yet:
# rsync log file for updates
#logfile = "/var/log/inorun.log"

# initial event to raise virtually on watched directory, maybe to start an
# initial full copy
#initevent = "IN_CREATE"
