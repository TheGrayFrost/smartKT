cmake_minimum_required(VERSION 3.1.0)

# set the project name
project(opr_overload CXX)


set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS_DEBUG "-gdwarf-4")


# add the executable
add_executable (overload overload.cpp)

