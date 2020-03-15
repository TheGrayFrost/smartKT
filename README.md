# TO RUN

1. Download the SmartKT tool (you may use `git clone https://github.com/TheGrayFrost/smartKT`)
2. Create a `projects` folder and `cd projects`
3. Git clone the project you want to run SmartKT on. (Example: `git clone https://github.com/glennrp/libpng`)
4. Move to the base directory (by using `cd ..`)
5. Copy the PIN tool into the PIN/PIN folder.
6. Run `python3 initialize.py projects/<projectName>`
7. Edit `runs.json` file. (Please use absolute paths)
8. Run `python3 examine.py runs.json`
9. Enjoy!

# TODO
[] Parallelize comments analysis part
[] System benchmarking for large projects
[] Check parallel execution for dynamic runtimes
[] Provide option for choosing what to run (static/dynamic/comments/vcs)
[] start vcs before initialize (if possible!), takes way long time though! 


# KNOWN ISSUES