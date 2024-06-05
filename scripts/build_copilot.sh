# setup
buildPath="build/copilot"
cd ..
rootPath=`pwd`
rm -rf build
mkdir build

# copy assets into build
cp -R copilot build
rm $buildPath/app/configs $buildPath/app/common
cp -R configs $buildPath/app
cp -R common $buildPath/app

# docker build
cd $buildPath
docker build -t copilot .
cd $rootPath
rm -rf build
