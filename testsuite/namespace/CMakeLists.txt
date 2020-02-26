cmake_minimum_required(VERSION 3.1.0)

# set the project name
project(namespace CXX)

set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS_DEBUG "-gdwarf-4")
set(CMAKE_CXX_FLAGS "-std=c++17")

add_executable (random random.cc main.cc)