#include <clang-c/Index.h>
#include <libxml/parser.h>
#include <libxml/tree.h>
#include <iostream>
#include <string>
#include <cstring>
#include <unordered_map>
#include <vector>
#include <fstream>

using std::unordered_map;
using std::to_string;


struct trav_data_t {
  xmlNodePtr ptr;
};


unordered_map<int, const char*> 
  storage_class_names,
  access_specifier_names;

// ise toh global rakhna padega uncle
CXTranslationUnit tu;

CXChildVisitResult
visitor(CXCursor cursor, CXCursor parent, CXClientData clientData)
{

  CXSourceLocation location = clang_getCursorLocation( cursor );
  // CXSourceLocation rangeStart = clang_getRangeStart(cursor);
  // CXSourceLocation rangeEnd = clang_getRangeStart(cursor);

  /** Only parse contents of the main file. */
  if( clang_Location_isFromMainFile( location ) == 0 ) {
    return CXChildVisit_Continue;
  }

  trav_data_t parentData = *(reinterpret_cast<trav_data_t*>(clientData));

  CXCursorKind cursorKind = clang_getCursorKind(cursor);
  CXString kindName = clang_getCursorKindSpelling(cursorKind);
  CXString spelling = clang_getCursorSpelling(cursor);
  CXString usr = clang_getCursorUSR(cursor);
  CXString mangledName = clang_Cursor_getMangling(cursor);

  CXType cursorType = clang_getCursorType(cursor);
  CXString typeSpelling = clang_getTypeSpelling(cursorType);

  CX_StorageClass storageClass = clang_Cursor_getStorageClass(cursor);

  CX_CXXAccessSpecifier accessSpecifier = clang_getCXXAccessSpecifier(cursor);


  xmlNodePtr curPtr = xmlNewChild(parentData.ptr, nullptr,
    BAD_CAST clang_getCString(kindName), nullptr);

  // printing all call expressions
  // std::cout << clang_getCString(kindName) << " " << (strcmp(clang_getCString(kindName), "CallExpr")) << "\n";
  if (strcmp(clang_getCString(kindName), "CallExpr") == 0)
  {
    std::cout << "FOUND\n\n";
    CXToken * Tokens;
    unsigned NumTokens;
    CXSourceRange Range = clang_getCursorExtent(cursor);
    CXSourceLocation Rstart = clang_getRangeStart(Range);
    CXSourceLocation Rend = clang_getRangeEnd(Range);
    
    CXFile locfile;
    unsigned line, column, offset;
    clang_getSpellingLocation(Rstart, &locfile, &line, &column, &offset);
    CXString fileName1 = clang_getFileName(locfile);
    std::string location_string(clang_getCString(fileName1));
    location_string += ":"+to_string(line);
    location_string += ":"+to_string(column);
    std::cout << location_string << "\n";
    clang_disposeString(fileName1);

    CXString fileName2 = clang_getFileName(locfile);
    location_string = clang_getCString(fileName2);
    location_string += ":"+to_string(line);
    location_string += ":"+to_string(column);
    std::cout << location_string << "\n";
    clang_disposeString(fileName2);
    
    clang_tokenize(tu, Range, &Tokens, &NumTokens);
    for (int i = 0; i < NumTokens; ++i)
    {
      CXString curtok = clang_getTokenSpelling(tu, Tokens[i]);
      std::cout << clang_getCString(curtok) << " ";
      clang_disposeString(curtok);
    }
    std::cout << "\n";
    clang_disposeTokens(tu, Tokens, NumTokens);
  }

  xmlNewProp(curPtr, BAD_CAST "id",
    BAD_CAST to_string(clang_hashCursor(cursor)).c_str());

  xmlNewProp(curPtr, BAD_CAST "spelling",
    BAD_CAST clang_getCString(spelling));

  xmlNewProp(curPtr, BAD_CAST "usr",
    BAD_CAST clang_getCString(usr));

  xmlNewProp(curPtr, BAD_CAST "mangled_name",
    BAD_CAST clang_getCString(mangledName));

  xmlNewProp(curPtr, BAD_CAST "type_spelling",
    BAD_CAST clang_getCString(typeSpelling));

  // long long typeSize = clang_Type_getSizeOf(cursorType);
  // xmlNewProp(curPtr, BAD_CAST "type_size",
  //   BAD_CAST to_string(typeSize).c_str());

  if( storageClass != CX_SC_Invalid && storageClass != CX_SC_None ) {
    xmlNewProp(curPtr, BAD_CAST "storage_class",
        BAD_CAST storage_class_names[storageClass] );
  }

  if( accessSpecifier != CX_CXXInvalidAccessSpecifier ) {
    xmlNewProp(curPtr, BAD_CAST "access_specifier",
        BAD_CAST access_specifier_names[accessSpecifier]);
  }

  CXFile file;
  unsigned line, column, offset;
  // note: clang_getSpellingLocation gives location of the #define in case of macros
  // note: we need location of the actual token that clang_getExpansionLocation gives
  clang_getExpansionLocation(location, &file, &line, &column, &offset);
  CXString fileName = clang_getFileName(file);

  std::string location_string;
  location_string += clang_getCString(fileName);
  location_string += ":"+to_string(line);
  location_string += ":"+to_string(column);
  location_string += ":"+to_string(offset);
  xmlNewProp(curPtr, BAD_CAST "location",
      BAD_CAST location_string.c_str());

  clang_disposeString( kindName );
  clang_disposeString( spelling );
  clang_disposeString( usr );
  clang_disposeString( mangledName );
  clang_disposeString( typeSpelling );
  clang_disposeString( fileName );

  {
    CXCursor referencedCursor = clang_getCursorReferenced(cursor);
    if( !clang_Cursor_isNull(referencedCursor) ) {
      xmlNewProp(curPtr, BAD_CAST "ref_id",
          BAD_CAST to_string( clang_hashCursor(referencedCursor) ).c_str());
    }
  }

  {
    CXCursor definitionCursor = clang_getCursorDefinition(cursor);
    if( !clang_Cursor_isNull(definitionCursor) ) {
      xmlNewProp(curPtr, BAD_CAST "def_id",
          BAD_CAST to_string( clang_hashCursor(definitionCursor) ).c_str());
    }
  }

  {
    CXCursor semanticParent = clang_getCursorSemanticParent(cursor);
    if( !clang_Cursor_isNull(semanticParent) ) {
      xmlNewProp(curPtr, BAD_CAST "sem_parent_id",
        BAD_CAST to_string( clang_hashCursor(semanticParent) ).c_str());
    }
  }

  {
    CXCursor lexicalParent = clang_getCursorLexicalParent(cursor);
    if( !clang_Cursor_isNull(lexicalParent) ) {
      xmlNewProp(curPtr, BAD_CAST "lex_parent_id",
        BAD_CAST to_string( clang_hashCursor(lexicalParent) ).c_str());
    }
  }


  trav_data_t curData{curPtr};

  clang_visitChildren( cursor, visitor, &curData );

  return CXChildVisit_Continue;
}


int main( int argc, char** argv ) {

  for(std::pair<int, const char*> p:
    std::vector<std::pair<int, const char*>>
      {{CX_SC_Invalid,"Invalid"},
      {CX_SC_None,"None"},
      {CX_SC_Extern,"Extern"},
      {CX_SC_Static,"Static"},
      {CX_SC_PrivateExtern,"PrivateExtern"},
      {CX_SC_OpenCLWorkGroupLocal,"OpenCLWorkGroupLocal"},
      {CX_SC_Auto,"Auto"},
      {CX_SC_Register,"Register"}} ) {
    storage_class_names.emplace(p.first, p.second);
  }

  for(std::pair<int, const char*> p:
    std::vector<std::pair<int, const char*>>
      { {CX_CXXInvalidAccessSpecifier, "Invalid"},
      {CX_CXXPublic, "Public"},
      {CX_CXXProtected, "Protected"},
      {CX_CXXPrivate, "Private"} }) {
    access_specifier_names.emplace(p.first, p.second);
  }


  if( argc < 6 ) {
    fprintf(stderr, "Usage : %s <ast_file> <out_base> <xml_ext> <call_ext> <funcinfo_ext>\n", argv[0]);
    return -1;
  }

  // output files
  std::string outbase(argv[2]);
  std::string outxml = outbase + std::string(argv[3]);
  std::string outcall = outbase + std::string(argv[4]);
  std::string outfuncinfo = outbase + std::string(argv[5]);

  std::ofstream foutcall(outcall.c_str());
  std::ofstream foutfuncinfo(outfuncinfo.c_str());

  CXIndex index = clang_createIndex(0, 1);
  tu = clang_parseTranslationUnit(index, argv[1], nullptr, 0, nullptr, 0, CXTranslationUnit_DetailedPreprocessingRecord);
  // tu = clang_createTranslationUnit(index, argv[1]);

  if( !tu ) {
    fprintf(stderr, "Error while parsing %s.\n", argv[1]);
    return -1;
  }

  LIBXML_TEST_VERSION;

  xmlDocPtr doc = nullptr;
  xmlNodePtr root_node = nullptr;

  /* Creates a new document, a node and set it as a root node */
  doc = xmlNewDoc(BAD_CAST "1.0");
  root_node = xmlNewNode(nullptr, BAD_CAST "TranslationUnit");
  xmlDocSetRootElement(doc, root_node);

  /* Creates a DTD declaration. Isn't mandatory. */
  xmlCreateIntSubset(doc, BAD_CAST "TranslationUnit",
    nullptr, BAD_CAST "smartkt.dtd");

  /* Get root cursor. */
  CXCursor rootCursor  = clang_getTranslationUnitCursor( tu );

  trav_data_t root_data{root_node};

  /* DFT over syntax tree. */
  clang_visitChildren( rootCursor, visitor, &root_data );

  /* Dump document to stdio or file */
  xmlSaveFormatFileEnc(outxml.c_str() , doc, "UTF-8", 1);

  /* Free the document */
  xmlFreeDoc(doc);

  /* Free global variables that may have been allocated by libclang. */
  clang_disposeTranslationUnit( tu );
  clang_disposeIndex( index );

  /* Free the global variables that may have been allocated by the parser. */
  xmlCleanupParser();
  xmlMemoryDump();

  foutcall.close();
  foutfuncinfo.close();

  return 0;
}

