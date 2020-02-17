cmake_minimum_required(VERSION 3.1.0)

# set the project name
project(simple CXX)

set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS_DEBUG "-gdwarf-4")

# add the executable
add_library (random.o OBJECT random.cc)
add_executable (base base.cc foo.cc)