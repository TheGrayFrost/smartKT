cmake_minimum_required(VERSION 3.1.0)

# set the project name
project(extern CXX)

set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS_DEBUG "-gdwarf-4")

# create .so
add_library(foo SHARED A.cc B.cc)

# add the executable
add_executable (test C.cc)
target_link_libraries (test foo)

