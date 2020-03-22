# TO RUN

1. Download the SmartKT tool (you may use `git clone --recursive https://github.com/TheGrayFrost/smartKT`)
2. Create a `projects` folder and `cd projects`
3. Git clone the project you want to run SmartKT on. (Example: `git clone https://github.com/glennrp/libpng`)
4. Move to the base directory (by using `cd ..`)
5. Download the [PIN toolkit](https://software.intel.com/en-us/articles/pin-a-binary-instrumentation-tool-downloads) into PIN/PIN folder.
6. Run `./initialize.py projects/<projectName>`
7. Create `runs.json` file. (Please use absolute paths. `sample_runs.json` provided for `libpng`)
8. Run `./examine.py runs.json`
9. Enjoy!

# TODO
- [ ] Parallelize comments analysis part
- [ ] System benchmarking for large projects
- [ ] Check parallel execution for dynamic runtimes
- [ ] Provide option for choosing what to run (static/dynamic/comments/vcs)
- [ ] start vcs before initialize (if possible!), takes way long time though! 


# KNOWN ISSUES