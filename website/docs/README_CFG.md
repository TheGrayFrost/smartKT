# Introduction
The dumped information of BasicBlocks and CallGraphs are neither sufficient nor correct.
For details, please read my (spandankumarsahu) MTP thesis's corresponding chapter

# Algorithm
Detailed algorithm explained in the thesis. For implementational algorithm, please
follow source code. Overall execution flow is as follows:
  1. Read the `data/final.cfg` to create a first-pass basic block graph and a call graph.
  2. List all non-artificial functions
  3. For all non-artificial functions:
      i. Find list of all instances of call expressions in the function
      ii. Traverse the basic blocks in a BFS manner
      iii. For each basic block, find the call expression instances which are present in the block
      iv. Arrange those "contained" call expressions in the expected order in which they might be called
      v. Split the basic block and reconfigure edges between the functions of the called expressions and the basic block
  4. For each runtime trace:
      i. if the instruction type is read: identify the block it is contained in, and mark it covered
      ii. if the instruction type is call: identify the block it is contained in. Handle unhandled constructors/destructors,
          runtime polymorphism function calls and normal function calls. Push the callee function in the stack
      iii. if the instruction type is return: verify whether the return is compliant with the graph we have
  5. Export the data into suitable formats for use by `app.py`

# Flaws (and reasons)
* column information from PIN is not available, resulting in inaccuracy of basic Block's column information,
  in case a basic block was split
* destructor information is not available from static information, and hence it is not linked to the dynamic trace,
  resulting in having to manually identify destructors. Hacky and inefficient and prone to errors.

# Future Works
* Extract exact pieces of code from source files and update the block2label dictionary (and update corresponding website)
  This will then display the source code, instead of basic block's ID
