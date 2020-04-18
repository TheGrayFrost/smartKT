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

struct TokenList {
  CXTranslationUnit tu;
  CXToken* tokens = nullptr;
  unsigned num_tokens = 0;
};

using SourceLocation = std::pair<unsigned, unsigned>;
// typedef std::pair<unsigned, unsigned> SourceLocation;

CXIndex clang_index;
std::unordered_map<std::string, TokenList> source_files;

static std::string const delim = "\t";
std::ifstream infile;
std::ofstream outfile;

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
  line = line + "\tCALLEXPR\n";
  outfile << line;

  while( std::getline(infile, line) ) {
    char filename_str[2048], funcname_str[2048], nodeid_str[64];
    SourceLocation from, to;

    std::sscanf(line.c_str(), "%s\t%u:%u::%u:%u\t%s\t%s",
      filename_str, &from.first, &from.second,
      &to.first, &to.second, funcname_str, nodeid_str);

    std::string filename (filename_str);
    std::string funcname (funcname_str);

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

    outfile << filename
      << delim << from.first << ":" << from.second
      << "::" << to.first << ":" << to.second
      << delim << funcname
      << delim << nodeid_str << delim;

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

    bool first_token = true;
    while( true ) {
      CXSourceLocation tokloc =
        clang_getTokenLocation(tokenlist.tu, *iter);
      SourceLocation token_location;
        clang_getSpellingLocation(tokloc, nullptr,
          &token_location.first, &token_location.second, nullptr);

      // std::cerr << std::endl << "[" << token_location.first
      //   << " " << token_location.second << "]" << std::endl;

      if( token_location >= to ) break;

      CXString spelling_str = clang_getTokenSpelling(tokenlist.tu, *iter);
      const char* token_str = clang_getCString(spelling_str);

      bool good_token = true;
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

  for(auto &element: source_files) {
    TokenList tokenlist; std::tie(std::ignore, tokenlist) = element;
    clang_disposeTokens(tokenlist.tu, tokenlist.tokens, tokenlist.num_tokens);
    clang_disposeTranslationUnit(tokenlist.tu);
  }
  clang_disposeIndex(clang_index);

  return 0;
}
