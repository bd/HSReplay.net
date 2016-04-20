echo "Creating AWS Lambda Deployment Zip"
cwd=$(pwd)
rm ./hsreplay.zip
cd ../hsreplaynet
zip -r $cwd/hsreplay.zip ./*
cd $VIRTUAL_ENV/lib/python2.7/site-packages
zip -r $cwd/hsreplay.zip ./*

