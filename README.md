# TO RUN

1. Download the SmartKT tool (you may use `git clone --recursive https://github.com/TheGrayFrost/smartKT`)
2. Create a `projects` folder and `cd projects`
3. Git clone the project you want to run SmartKT on. (Example: `git clone https://github.com/glennrp/libpng`)
4. Move to the base directory (by using `cd ..`)
5. Download the [PIN toolkit](https://software.intel.com/en-us/articles/pin-a-binary-instrumentation-tool-downloads) into PIN/PIN folder.
6. Run `./initialize.py projects/<projectName>`
7. Create `runs.json` file. (Please use absolute paths. `sample_runs.json` provided for `libpng`)
Note: For the `testsuite` the runs.json have been placed in the folder itself (e.g. `testsuite/extern/ contains runs_extern.json`)
8. Run `./examine.py runs.json`
9. Enjoy!

# DEPENDENCIES

Compiler
1. gcc >= 8: https://gcc.gnu.org/gcc-8/
2. g++ >= 8: https://packages.ubuntu.com/bionic/g++-8

C/C++ libraries
1. clang >= 9: https://releases.llvm.org/download.html
2. libxml2-dev: http://xmlsoft.org/downloads.html

Python:
1. python >= 3.6: https://www.python.org/downloads/
2. pyelftools
3. pygithub

# EXPECTED PROJECT ATTRIBUTES

Our tool expects your projects to:
* be C/C++ based
* use makefiles for project build
* use CMake as the makefile generator
* support verbose makes and debug build
* work on Unix-based OSes
* contain testsuite we may use for runtime tracing

# TODO
- [X] Parallelize comments analysis part
- [ ] System benchmarking for large projects
- [X] Check parallel execution for dynamic runtimes
- [ ] Add support for specifying custom build script

# KNOWN ISSUES

Refer here: 
https://docs.google.com/document/d/19lsyo48fotI4L1GyUDDhXYHXvNn6PpdtX_1TXbNAsVM/edit?usp=sharing
