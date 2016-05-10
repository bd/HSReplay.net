echo "Creating AWS Lambda Deployment Zip"
cwd=$(pwd)
rm ./hsreplay.zip
cd ../hsreplaynet
zip -r $cwd/hsreplay.zip ./*
cd $VIRTUAL_ENV/lib/python2.7/site-packages
zip -r $cwd/hsreplay.zip ./*
hsreplay_lib_path=$(cat hsreplay.egg-link | head -n 1)
cd $hsreplay_lib_path
zip -r $cwd/hsreplay.zip ./hsreplay/*