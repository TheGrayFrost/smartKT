cmake_minimum_required(VERSION 3.1)

project(threads CXX)

set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS_DEBUG "-g")
set(CMAKE_CXX_FLAGS "-std=c++17")

# add the executable
find_package (Threads)
add_executable (thread main.cpp try.cpp)
target_link_libraries (thread ${CMAKE_THREAD_LIBS_INIT})
