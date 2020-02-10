set -x
cd /home/spandan/MTPSMARTKT/github/smartKT/projects/smallproj
rm -rf build
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j$(nproc) VERBOSE=1 > make_log.txt
mkdir -p /home/spandan/MTPSMARTKT/github/smartKT/outputs/smallproj
mv make_log.txt /home/spandan/MTPSMARTKT/github/smartKT/outputs/smallproj/
