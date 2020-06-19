# Introduction
The dumped information of BasicBlocks and CallGraphs are neither sufficient nor correct.
For details, please read my (spandankumarsahu) MTP thesis's corresponding chapter

# Algorithm
Detailed algorithm explained in the thesis. For implementational algorithm, please
follow source code

# Flaws (and reasons)
* column information from PIN is not available, resulting in inaccuracy of basic Block's column information,
  in case a basic block was split
* destructor information is not available from static information, and hence it is not linked to the dynamic trace,
  resulting in having to manually identify destructors. Hacky and inefficient and prone to errors.

# Future Works
* Extract exact pieces of code from source files and update the block2label dictionary (and update corresponding website)
  This will then display the source code, instead of basic block's ID
