# Source Level (Static) Control flow Graph

## BUILD
* cd cfg
* make

## RUN
* ./cfg <filename>.ast

# Output Format
The output is a concatenation of graph information of BasicBlock information and Call Graph information. The two information are separated by a randomly generated key St5D7yHzyE5WRpHRGuGVB6r4t4HK47TRS69Gka7Pfc2d2wArVrmyPtUZbEUxVMrZ.

Please note that, basic block information could be extracted for only functions.
Clang's analysis module is used to derive this. This information is represented as follows:
The first line is
<function_name> <function_location>
The second line is the number of basic blocks by Clang
<numBasicBlocks>
Then there are <numBasicBlocks> lines each of the type:
<basicBlockID> <startLine, startCol, endLine, endCol> <predecessorsIDs> <successorIDs>

The basic block information of each function is concatenated in the same fashion.
There are special BasicBlocks called ENTRY and EXIT and each function (basic block group)
has one of each. ENTRY block doesn't have any predecesor and EXIT block doesn't have any successors, yet. ENTRY and EXIT are fictional, hence they have arbitrary locations

The call graph information is represented as follows:
<functionMangledName>: [list of functions it calls]
There is a special node called <root> and it calls all possible functions in the AST.

# Algorithm
For algorithm see the comments inside the code

# Known Bugs
* Works on C++11 and below
* Do not use any header file that internally uses "stddef.h". Use C-style headers
  i.e. use specific headers for the functions, do not include a superset header file
  like bits/stdc++ or iostream
