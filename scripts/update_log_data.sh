#!/bin/bash
BASEDIR="$(readlink -f $(dirname $0))"
DATADIR="$BASEDIR/../data"
GITDIR="$DATADIR/hsreplay-test-data"
TESTDATA_URL="https://github.com/HearthSim/hsreplay-test-data.git"

set -e

mkdir -p "$DATADIR"

if [[ -d "$GITDIR" ]]; then
	echo "Updating $GITDIR"
	git -C "$GITDIR" fetch --all
	git -C "$GITDIR" reset --hard origin/master
else
	git clone "$TESTDATA_URL" "$GITDIR"
fi

