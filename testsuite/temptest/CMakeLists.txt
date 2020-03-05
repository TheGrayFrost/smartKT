cmake_minimum_required(VERSION 3.1.0)
set (CMAKE_CXX_STANDARD 14)

# set the project name
project(temptest CXX)

set(CMAKE_BUILD_TYPE Debug)
set(CMAKE_CXX_FLAGS_DEBUG "-gdwarf-4")

include_directories ("${PROJECT_SOURCE_DIR}/foo")
# add_subdirectory(foo)

# add the executable

add_executable(driver.out driver.cc)
# target_link_libraries (driver.out foo)

add_executable(test.out template_test.cc)
