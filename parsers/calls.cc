#include <clang-c/Index.h>

#include <cstdio>
#include <algorithm>
#include <iostream>
#include <sstream>
#include <fstream>

#include <cstring>
#include <string>

#include <utility>
#include <vector>
#include <unordered_map>

/*
  This tool is used to tokenize call expressions and emit the .calls.tokens files for
  source files.
  The input is a list of call expression records (in .calls.temp file).
  (See ast2xml and its invocation in initialize.py for more details.)

  For each such call expression, we know its location bounds in the source code,
  so we can read the file and seek to the line number / column number,
  and start reading the file from that position.
  But the resulting string must also be tokenized.

  All of the above problems can be solved by using libclang's tokenizer.
  We perform an optimization, by tokenizing the entire TU once, and keeping
  the tokens and their locations in memory.

*/

// An object representing a list of tokens from some source file / header file.
struct TokenList {
  CXTranslationUnit tu; // consider this a pointer to a file
  CXToken* tokens = nullptr; // list of tokens in that file
  unsigned num_tokens = 0; // number of tokens in that list
};

// "SourceLocation" type for storing the location (line, col) of a token.
typedef std::pair<unsigned, unsigned> SourceLocation;

CXIndex clang_index;
std::unordered_map<std::string, TokenList> source_files;
// map file names to TokenLists. Also stores the set of files tokenized so far.

static std::string const delim = "\t";
std::ifstream infile; // .calls.temp file
std::ofstream outfile; // .calls.tokens file

int main(int argc, char* argv[]) {

  if( argc !=3 ) {
    fprintf(stderr, "Usage : %s <temp_file> <final_file>\n", argv[0]);
    return -1;
  }

  clang_index = clang_createIndex(0, 0);

  infile.open(argv[1]);
  outfile.open(argv[2]);

  std::string line;

  std::getline(infile, line);
  line = line + "\tCALLEXPR\n"; // update header file
  outfile << line;

  while( std::getline(infile, line) ) { // iterate over lines (records)

    char filename_str[2048], funcname_str[2048], nodeid_str[64];
    SourceLocation from, to;

    // read file and location data from formatted string
    // "from" and "to" are the locations of the first and last tokens. 
    std::sscanf(line.c_str(), "%s\t%u:%u::%u:%u\t%s\t%s",
      filename_str, &from.first, &from.second,
      &to.first, &to.second, funcname_str, nodeid_str);

    std::string filename (filename_str);
    std::string funcname (funcname_str);

    // If source file has not been seen so far, read and tokenize it.
    if( source_files.find(filename) == source_files.end() ) {
      TokenList tokenlist;
      tokenlist.tu = clang_createTranslationUnitFromSourceFile(
        clang_index, filename_str, 0, 0, 0, 0);
      CXCursor root_cursor = clang_getTranslationUnitCursor(tokenlist.tu);
      CXSourceRange tu_range = clang_getCursorExtent(root_cursor);
      tokenlist.tokens = nullptr;
      clang_tokenize(tokenlist.tu, tu_range,
        &tokenlist.tokens, &tokenlist.num_tokens);
      source_files.emplace(filename, tokenlist);
    }

    TokenList tokenlist = source_files[filename];

    // Print existing data.
    outfile << filename
      << delim << from.first << ":" << from.second
      << "::" << to.first << ":" << to.second
      << delim << funcname
      << delim << nodeid_str << delim;

    // Find the index of the first token, within the range ("from", "to"),
    // by doing a binary search.
    auto iter = std::lower_bound(
        tokenlist.tokens, tokenlist.tokens+tokenlist.num_tokens, from,
        [&]
        (CXToken const& token, SourceLocation const& ref_location) {
          CXSourceLocation tokloc =
            clang_getTokenLocation(tokenlist.tu, token);
          SourceLocation token_location;
          clang_getSpellingLocation(tokloc, nullptr,
            &token_location.first, &token_location.second, nullptr);
          return token_location < ref_location;
        });

    // Print all subsequent tokens until we reach the far side of location "to".
    bool first_token = true;
    while( true ) {
      CXSourceLocation tokloc =
        clang_getTokenLocation(tokenlist.tu, *iter);
      SourceLocation token_location;
        clang_getSpellingLocation(tokloc, nullptr,
          &token_location.first, &token_location.second, nullptr);

      // std::cerr << std::endl << "[" << token_location.first
      //   << " " << token_location.second << "]" << std::endl;

      if( token_location >= to ) break; // token out of range, break loop
      // else print this token.

      CXString spelling_str = clang_getTokenSpelling(tokenlist.tu, *iter);
      const char* token_str = clang_getCString(spelling_str);

      bool good_token = true; // Only print tokens without newlines in them. 
      // Only bad tokens that have been observed are multiline comments inside a call expression.
      if( std::strchr(token_str, '\n') ) {
        good_token = false;
      }

      if( good_token ) {
        outfile << token_str;
        if( first_token ){
          first_token = false;
        } else {
          outfile << " ";
        }
      }
      
      clang_disposeString(spelling_str);

      iter++;
    }

    outfile << std::endl;
  }

  infile.close();
  outfile.close();

  // Free all token lists from memory.
  for(auto &element: source_files) {
    TokenList tokenlist; std::tie(std::ignore, tokenlist) = element;
    clang_disposeTokens(tokenlist.tu, tokenlist.tokens, tokenlist.num_tokens);
    clang_disposeTranslationUnit(tokenlist.tu);
  }
  clang_disposeIndex(clang_index);

  return 0;
}
