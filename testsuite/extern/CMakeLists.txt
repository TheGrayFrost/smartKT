cmake_minimum_required(VERSION 3.1.0)

# set the project name
project(extern CXX)

set(CMAKE_CXX_COMPILER clang++)
set(CMAKE_CXX_FLAGS "--gcc-toolchain=/opt/rh/devtoolset-8/root/usr/")
set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS_DEBUG "-gdwarf-4")

# create .so
add_library(foo SHARED A.cc B.cc)

# add the executable
add_executable (test C.cc)
target_link_libraries (test foo)

