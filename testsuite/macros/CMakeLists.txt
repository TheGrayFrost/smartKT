cmake_minimum_required(VERSION 3.1.0)

# set the project name
project(macros C)

set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_C_FLAGS_DEBUG "-gdwarf-4")

# add the executable
add_executable (macro base.c foo.c)