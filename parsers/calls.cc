#include <clang-c/Index.h>
#include <iostream>

# define FILEHEADER "# FILENAME\tLINENUM\tFUNCNAME\tCALLNODEID\tCALLEXPR\n"

char const delim = '\t';
CXTranslationUnit tu;

CXChildVisitResult get_call_expressions
(CXCursor cursor, CXCursor parent, CXClientData) {
  CXCursorKind cursorKind = clang_getCursorKind(cursor);

  if( cursorKind == CXCursor_CallExpr ) {
    CXCursor refc = clang_getCursorReferenced(cursor);
    if( !clang_Cursor_isNull(refc) ) {

      /* Emit source location. */
      CXSourceLocation location = clang_getCursorLocation( cursor );
      CXFile file;
      CXString fileName;
      unsigned line, column;
      clang_getSpellingLocation(location, &file, &line, &column, nullptr);
      fileName = clang_getFileName(file);
      std::cout << clang_getCString(fileName);
      std::cout << delim << line;
      // std::cout << ":" << column;

      /* Get source and linkage identifiers. */
      CXString mangling = clang_Cursor_getMangling(refc);
      CXString usr = clang_getCursorUSR(refc);

      std::cout << delim << clang_getCString(mangling)
                << delim << clang_getCString(usr);

      CXToken* Tokens;
      unsigned NumTokens;
      CXSourceRange Range = clang_getCursorExtent(cursor);
      CXSourceLocation Rstart = clang_getRangeStart(Range);
      CXSourceLocation Rend = clang_getRangeEnd(Range);

      clang_tokenize(tu, Range, &Tokens, &NumTokens);
      for (unsigned i = 0; i < NumTokens; ++i) {
        CXString curtok = clang_getTokenSpelling(tu, Tokens[i]);
        if( i == 0 ) std::cout << delim;
        else std::cout << " ";
        std::cout << clang_getCString(curtok);
        clang_disposeString(curtok);
      }

      // if( clang_Cursor_isDynamicCall(cursor) ) {
      //   std::cout << delim << "Dynamic";
      // }

      std::cout << "\n";

      clang_disposeString(mangling);
      clang_disposeString(usr);
      clang_disposeTokens(tu, Tokens, NumTokens);
      clang_disposeString( fileName );
    }
  }

  clang_visitChildren(cursor, get_call_expressions, nullptr);
  return CXChildVisit_Continue;
}


int main(int argc, char* argv[]) {

  if( argc < 2 ) {
    fprintf(stderr, "usage: %s <ast_file>\n", argv[0]);
    return 1;
  }

  CXIndex index        = clang_createIndex(0, 1);
  tu = clang_createTranslationUnit( index, argv[1] );

  if( !tu ) {
    fprintf(stderr, "Error reading %s\n", argv[1]);
    return -1;
  }

  CXCursor rootCursor  = clang_getTranslationUnitCursor( tu );

  std::cout << FILEHEADER;
  clang_visitChildren(rootCursor, get_call_expressions, nullptr);

  /* Free global variables that may have been allocated by libclang. */
  clang_disposeTranslationUnit(tu);
  clang_disposeIndex(index);

  return 0;
}
