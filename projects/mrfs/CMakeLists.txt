cmake_minimum_required(VERSION 3.2)

project(mrfs CXX)

set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS_DEBUG "-gdwarf-4")
set(CMAKE_CXX_FLAGS "-std=c++17 -Wno-write-strings")

# add the executable
add_library(support SHARED fs.cpp in.cpp sb.cpp)
add_library(fsys SHARED filesys.cpp)
target_link_libraries (fsys support)
find_package (Threads)
add_executable (fstest1 test1.cpp)
target_link_libraries (fstest1 fsys)
add_executable (fstest2 test2.cpp)
target_link_libraries (fstest2 fsys)
add_executable (fstest3 test3.cpp)
target_link_libraries (fstest3 fsys ${CMAKE_THREAD_LIBS_INIT})