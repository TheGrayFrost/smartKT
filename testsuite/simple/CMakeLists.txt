cmake_minimum_required(VERSION 3.1.0)

# set the project name
project(simple CXX)
# set(CMAKE_CXX_COMPILER "/opt/rh/devtoolset-8/root/usr/bin/c++")
set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS_DEBUG "-gdwarf-4")
set(CMAKE_CXX_FLAGS "-std=c++17")

# add the executable
add_library (B SHARED foo.cc)
add_library (A SHARED bar.cc)
target_link_libraries (A B)
add_library (C SHARED rand.cc)
add_executable (base base.cc)
target_link_libraries (base C A)


# add_executable (random random.cc main.cc)