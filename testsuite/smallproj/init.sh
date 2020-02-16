set -x
cd /data/user-home/srijoni/PIN_Tests/smartKT/testsuite/smallproj
rm -rf build
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=1 ..
make -j$(nproc) VERBOSE=1 > make_log.txt
mkdir -p /data/user-home/srijoni/PIN_Tests/smartKT/outputs/smallproj
mv compile_commands.json /data/user-home/srijoni/PIN_Tests/smartKT/outputs/smallproj/
mv make_log.txt /data/user-home/srijoni/PIN_Tests/smartKT/outputs/smallproj/
