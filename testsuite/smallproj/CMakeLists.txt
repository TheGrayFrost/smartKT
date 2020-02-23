cmake_minimum_required(VERSION 2.8)

project(smallproj)

include_directories ("${PROJECT_SOURCE_DIR}/lib")
add_subdirectory(lib)

# add the executable
add_executable (inherit src/inherit.cpp)
target_link_libraries (inherit foo)

# add the executable
# add_executable (extern src/extern.cpp)
# target_link_libraries (extern bar)

# add the executable
# add_executable (template src/template.cpp)

# add the executable
find_package (Threads)
# add_executable (thread src/threading.cpp)
# target_link_libraries (thread ${CMAKE_THREAD_LIBS_INIT})
