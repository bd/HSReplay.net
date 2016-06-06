echo "Creating AWS Lambda Deployment Zip"

BASEDIR=$(readlink -f "$(dirname $0)/../..")
ZIPFILE="$BASEDIR/deploy/hsreplay.zip"
SITE_PACKAGES=$(python -c "import sys; print(sys.path[-1])")

rm -f "$ZIPFILE"

git -C "$BASEDIR" archive --format=zip HEAD -o "$ZIPFILE"

cd "$SITE_PACKAGES"
zip -r "$ZIPFILE" ./*

cd "$BASEDIR"
zip -r "$ZIPFILE" "hsreplaynet/local_settings.py"

echo "Written to $ZIPFILE"
