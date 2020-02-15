set -x
cd /data/user-home/srijoni/PIN_Tests/smartKT/testsuite/extern
rm -rf build
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Debug ..
make -j$(nproc) VERBOSE=1 > make_log.txt
mkdir -p /data/user-home/srijoni/PIN_Tests/smartKT/outputs/extern
mv make_log.txt /data/user-home/srijoni/PIN_Tests/smartKT/outputs/extern/
