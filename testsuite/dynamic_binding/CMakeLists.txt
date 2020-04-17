cmake_minimum_required(VERSION 3.1.0)

# set the project name
project(dynamic_binding CXX)


set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS_DEBUG "-gdwarf-4")


# add the executable
add_executable (dynamic dynamic.cpp)

