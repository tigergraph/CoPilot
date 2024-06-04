# setup
buildPath="build/ecc"
cd ..
rootPath=`pwd`
rm -rf build
mkdir build

# copy assets into build
cp -R eventual-consistency-service build/ecc
rm $buildPath/app/configs $buildPath/app/common
cp -R configs $buildPath/app
cp -R common $buildPath/app

# docker build
cd $buildPath
docker build -t ecc .
cd $rootPath
rm -rf build
