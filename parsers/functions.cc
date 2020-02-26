#include <clang-c/Index.h>
#include <iostream>

#define FILEHEADER "# FILENAME\tFUNCNODEID\tFUNCNAME\tNARGS\tARGTYPE*\tRETTYPE\n"
# define IDSIZE 11   // normal unsigned int has 10 digits.. we are padding with one extra zero
std::string FILEID; // FILEID passed to ast2xml

char const delim = '\t';
CXTranslationUnit tu;

std::string makeUniqueID (unsigned id)
{
  std::string p = std::to_string(id);
  p = FILEID + std::string(IDSIZE - p.length(), '0') + p;
  return p;
}

void emit_function_info
(CXCursor cursor, CXCursorKind cursorKind) {

  /* Emit source location. */
  CXCursor refc = clang_getCursorReferenced(cursor);
  if( !clang_Cursor_isNull(refc) ) {

    CXSourceLocation location = clang_getCursorLocation( cursor );
    CXFile file;
    CXString fileName;
    unsigned line;
    clang_getSpellingLocation(location, &file, &line, nullptr, nullptr);
    fileName = clang_getFileName(file);
    std::cout << clang_getCString(fileName);
    // std::cout << ":" << line;
    clang_disposeString( fileName );

    /* Emit generic function data. */
    // CXString usr = clang_getCursorUSR(refc);
    CXString mangling = clang_Cursor_getMangling(refc);
  
    // CXString spelling = clang_getCursorSpelling(cursor);
    CXType cursor_type = clang_getCursorType( cursor );

    CXString result_type = clang_getTypeSpelling(
      clang_getResultType( cursor_type ));

    // Pretty printed function signature with arguments.
    // CXString display_name = clang_getCursorDisplayName(cursor);
    std::cout << delim << makeUniqueID(clang_hashCursor(cursor));

    // std::cout << delim << clang_getCString(usr);
    std::cout << delim << clang_getCString(mangling);

    // std::cout << delim << clang_getCString(spelling);

    // std::cout << delim << clang_getCString(display_name);

    // Names of individual argument types included in display_name.
    int nargs = clang_Cursor_getNumArguments(cursor);
    std::cout << delim << nargs;
    for( int i = 0; i < nargs; i++ ) {
      CXCursor arg_cursor = clang_Cursor_getArgument(cursor, i);
      // CXString arg_spelling = clang_getCursorSpelling(arg_cursor);
      CXType arg_type = clang_getCursorType(arg_cursor);
      CXString arg_type_spelling = clang_getTypeSpelling(arg_type);
      std::cout << delim << clang_getCString(arg_type_spelling) ;
                // << " "  << clang_getCString(arg_spelling);
      clang_disposeString(arg_type_spelling);
      // clang_disposeString(arg_spelling);
    }

    std::cout << delim << clang_getCString(result_type);

    /* C++ class/struct method declaration metadata. */
    // if( cursorKind == CXCursor_CXXMethod ) {
    //   if( clang_CXXMethod_isStatic(cursor) )
    //     std::cout << delim << "static";
    //   if( clang_CXXMethod_isPureVirtual(cursor) )
    //     std::cout << delim << "pure_virtual";
    //   else if( clang_CXXMethod_isVirtual(cursor) )
    //     std::cout << delim << "virtual";
    //   // not to be confused with default constructor
    //   if( clang_CXXMethod_isDefaulted(cursor) )
    //     std::cout << delim << "defualted";
    // }

    /* C++ constructor declaration metadata. */
    // if( cursorKind == CXCursor_Constructor ) {
    //   if( clang_CXXConstructor_isConvertingConstructor(cursor) )
    //     std::cout << delim << "converting";
    //   if( clang_CXXConstructor_isCopyConstructor(cursor) )
    //     std::cout << delim << "copy";
    //   if( clang_CXXConstructor_isMoveConstructor(cursor) )
    //     std::cout << delim << "move";
    //   if( clang_CXXConstructor_isDefaultConstructor(cursor) )
    //     std::cout << delim << "default";
    // }

    // clang_disposeString(display_name);
    clang_disposeString(result_type);
    clang_disposeString(mangling);
    // clang_disposeString(spelling);
    // clang_disposeString(usr);
  }
}


CXChildVisitResult get_function_info
(CXCursor cursor, CXCursor parent, CXClientData) {
  CXCursorKind cursorKind = clang_getCursorKind(cursor);

  if( clang_isDeclaration(cursorKind) &&
      clang_equalCursors(cursor, clang_getCanonicalCursor(cursor)) ) {
      CXString kindName = clang_getCursorKindSpelling(cursorKind);

      switch(cursorKind) {
        // case CXCursor_FunctionTemplate :
        case CXCursor_Constructor :
        case CXCursor_Destructor :
        case CXCursor_CXXMethod :
        case CXCursor_FunctionDecl :
          // std::cout << clang_getCString(kindName);
          emit_function_info(cursor, cursorKind);
          std::cout << "\n";
        default: ;
      }

      clang_disposeString(kindName);
  }

  clang_visitChildren(cursor, get_function_info, nullptr);
  return CXChildVisit_Continue;
}


int main(int argc, char* argv[]) {

  if( argc < 3 ) {
    fprintf(stderr, "Usage : %s <file_num> <ast_file>\n", argv[0]);
    return -1;
  }

  FILEID = std::string(argv[1]);

  CXIndex index = clang_createIndex( 0, 1 );
  tu = clang_createTranslationUnit( index, argv[2] );

  if( !tu ) {
    fprintf(stderr, "Error while reading / parsing %s\n", argv[2]);
    return -1;
  }

  CXCursor rootCursor  = clang_getTranslationUnitCursor( tu );

  std::cout << FILEHEADER;
  clang_visitChildren(rootCursor, get_function_info, nullptr);

  /* Free global variables that may have been allocated by libclang. */
  clang_disposeTranslationUnit(tu);
  clang_disposeIndex(index);

  return 0;
}
