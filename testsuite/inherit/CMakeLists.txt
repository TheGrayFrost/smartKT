cmake_minimum_required(VERSION 2.8)

project(inherit CXX)

set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS_DEBUG "-gdwarf-4")
set(CMAKE_CXX_FLAGS "-std=c++17")

include_directories ("${PROJECT_SOURCE_DIR}/lib")
add_subdirectory(lib)

# add the executable
add_executable (inherit src/inherit.cpp)
target_link_libraries (inherit foo)