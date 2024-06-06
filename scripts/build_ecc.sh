# setup
buildPath="build/ecc"
cd ..
rootPath=`pwd`
rm -rf build
mkdir build

# copy assets into build
cp -R eventual-consistency-service $buildPath
rm $buildPath/app/configs $buildPath/app/common
cp -R configs $buildPath/app

# docker build
docker build -t ecc -f eventual-consistency-service/Dockerfile .
rm -rf build
