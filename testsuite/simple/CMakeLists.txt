cmake_minimum_required(VERSION 3.1.0)

# set the project name
project(extern CXX)

set(CMAKE_CXX_COMPILER clang++)
set(CMAKE_CXX_FLAGS "--gcc-toolchain=/opt/rh/devtoolset-8/root/usr/")
set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS_DEBUG "-gdwarf-4")

# add the executable
add_executable (base base.cc foo.cc)