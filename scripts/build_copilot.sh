# setup
buildPath="build/copilot"
cd ..
rm -rf build
mkdir build

# copy assets into build
cp -R copilot $buildPath
cp -R configs $buildPath/app

# docker build
docker build -t copilot -f copilot/Dockerfile .
rm -rf build
