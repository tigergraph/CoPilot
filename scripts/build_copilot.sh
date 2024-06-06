# setup
buildPath="build/copilot"
cd ..
rm -rf build
mkdir build

# copy assets into build
cp -R copilot $buildPath
rm $buildPath/app/configs $buildPath/app/common
cp -R configs $buildPath/app

# docker build
docker build -t copilot -f copilot/Dockerfile .
rm -rf build
