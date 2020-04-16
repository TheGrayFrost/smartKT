cmake_minimum_required(VERSION 3.1)

project(smallproj)

set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS_DEBUG "-gdwarf-4")
set(CMAKE_C_FLAGS_DEBUG "-gdwarf-4")
set(CMAKE_CXX_FLAGS "-std=c++17")

# add the executable

add_library(foo SHARED foo.cpp)
add_executable (ptrtest main.cpp)
target_link_libraries (ptrtest foo)

add_library(fooC SHARED fooC.c)
add_executable (ptrtestC mainC.c)
target_link_libraries (ptrtestC fooC)