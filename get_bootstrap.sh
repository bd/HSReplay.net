#!/bin/bash
VERSION="3.3.6"
PKGNAME="bootstrap-$VERSION-dist"
SOURCE="https://github.com/twbs/bootstrap/releases/download/v$VERSION/$PKGNAME.zip"
BASEDIR="$(readlink -f $(dirname $0))"
STATICDIR="$BASEDIR/hsreplaynet/static"
OUTDIR="$STATICDIR/bootstrap"
ZIPFILE="$OUTDIR/bootstrap.zip"

set -e

mkdir -p "$OUTDIR"
wget "$SOURCE" -O "$ZIPFILE"
unzip "$ZIPFILE" -d "$OUTDIR"
mv "$OUTDIR/$PKGNAME"/{css,js,fonts} "$OUTDIR"
rmdir "$OUTDIR/$PKGNAME"
rm "$ZIPFILE"
