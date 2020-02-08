#include <clang-c/Index.h>
#include <iostream>

#include <libxml/parser.h>
#include <libxml/tree.h>

#include <string>
#include <cstring>

#include <map>

#define DEBUG true

struct trav_data_t {
  CXSourceLocation cur_loc; // Location of current cursor.
  xmlNodePtr xml_ptr; // XML node corresponding to current cursor.
};

std::map<std::string, xmlNodePtr> template_map; //keeps a map of templateDecl id to their parents

CXChildVisitResult
visitor(CXCursor cursor, CXCursor, CXClientData clientData) {
  auto parentData = (reinterpret_cast<trav_data_t*>(clientData));

  CXCursorKind cursorKind = clang_getCursorKind(cursor);
  CXString kindName = clang_getCursorKindSpelling(cursorKind);
  xmlNodePtr cur_ptr = xmlNewChild(parentData->xml_ptr, nullptr,
    BAD_CAST clang_getCString(kindName), nullptr);
  clang_disposeString( kindName );

  trav_data_t nodeData{clang_getNullLocation(), cur_ptr};

  // set cursor id
  std::string nodeid = std::to_string(clang_hashCursor(cursor));
  xmlNewProp(cur_ptr, BAD_CAST "id",
    BAD_CAST nodeid.c_str());

  // set cursor spelling
  {
    CXString spelling = clang_getCursorSpelling(cursor);
    const char* spelling_cstr = clang_getCString(spelling);
    if( std::strlen(spelling_cstr) > 0 )
      xmlNewProp(cur_ptr, BAD_CAST "spelling", BAD_CAST spelling_cstr);
    clang_disposeString( spelling );
  }

  CXSourceLocation location = clang_getCursorLocation( cursor );

  // Add location info.
  if( ! clang_equalLocations(parentData->cur_loc, location) ) {
    CXFile file, par_file;
    CXString fileName;
    unsigned line, column, offset;
    clang_getSpellingLocation(location, &file, &line, &column, &offset);
    clang_getSpellingLocation(parentData->cur_loc,
      &par_file, nullptr, nullptr, nullptr);
    if( ! clang_File_isEqual(par_file, file) ) {
      fileName = clang_getFileName(file);
      xmlNewProp(cur_ptr, BAD_CAST "file",
        BAD_CAST clang_getCString(fileName));
      clang_disposeString( fileName );
    }
    xmlNewProp(cur_ptr, BAD_CAST "line",
      BAD_CAST std::to_string(line).c_str());
    xmlNewProp(cur_ptr, BAD_CAST "col",
      BAD_CAST std::to_string(column).c_str());
    // xmlNewProp(cur_ptr, BAD_CAST "off",
    //   BAD_CAST std::to_string(offset).c_str());
  }
  nodeData.cur_loc = location;

  // Add cursor extent.
  {
    CXSourceRange Range = clang_getCursorExtent(cursor);
    CXSourceLocation Rstart = clang_getRangeStart(Range);
    CXSourceLocation Rend = clang_getRangeEnd(Range);
    unsigned line, column;
    // range start
    clang_getSpellingLocation(Rstart, nullptr, &line, &column, nullptr);
    std::string st = "[" + std::to_string(line) + ":" + std::to_string(column) + "]";
    xmlNewProp(cur_ptr, BAD_CAST "range.start", BAD_CAST st.c_str());
    // range end
    clang_getSpellingLocation(Rend, nullptr, &line, &column, nullptr);
    std::string en = "[" + std::to_string(line) + ":" + std::to_string(column) + "]";
    xmlNewProp(cur_ptr, BAD_CAST "range.end", BAD_CAST en.c_str());
  }

  // Cursor type info
  {
    CXType cursor_type = clang_getCursorType(cursor);
    CXString type_spelling = clang_getTypeSpelling(cursor_type);
    const char * type_spelling_cstr = clang_getCString(type_spelling);
    if( std::strlen(type_spelling_cstr) > 0 ) {
      xmlNewProp(cur_ptr, BAD_CAST "type",
        BAD_CAST type_spelling_cstr);
      /*
      long long typesize = clang_Type_getSizeOf(cursor_type);
      if (typesize > 0)
        xmlNewProp(cur_ptr, BAD_CAST "size",
          BAD_CAST std::to_string(typesize).c_str());
      /* 
        @Vishesh(26 Jan '20): 
          - only errors in children of function templates are okay, as typesizes can't be inferred
          - the errors may be in their template params, function args, results
      *#/
      else if (DEBUG)
        std::cout << "ERROR: " << nodeid << " " << cur_ptr->name << " SIZE: " << typesize << "\n";
      */
    }
    clang_disposeString( type_spelling );
  }

  // Cursor references.
  { // Add USR if non empty
    CXString usr = clang_getCursorUSR(cursor);
    const char * usr_cstr = clang_getCString(usr);
    if( std::strlen(usr_cstr) > 0 )
      xmlNewProp(cur_ptr, BAD_CAST "usr", BAD_CAST usr_cstr);
    clang_disposeString( usr );
  }

  // add mangled name for function calls
  // {
  //   if( cursorKind == CXCursor_CallExpr )
  //   {
  //     CXCursor refc = clang_getCursorReferenced(cursor);
  //     if( !clang_Cursor_isNull(refc) ) {
  //       CXString mangling = clang_Cursor_getMangling(refc);
  //       const char * mn = clang_getCString(mangling);
  //       if( std::strlen(mn) > 0 ) 
  //       {
  //         xmlNewProp(cur_ptr, BAD_CAST "mangling",
  //         BAD_CAST mn);
  //       }
  //       else
  //         std::cout << "ERROR\n\n";
  //       clang_disposeString(mangling);
  //     }
  //   }
  // }


  { // Add lexical / semantic parents
    CXCursor lexicalParent = clang_getCursorLexicalParent(cursor);
    if( !clang_Cursor_isNull(lexicalParent) ) {
      CXString usr = clang_getCursorUSR(lexicalParent);
      const char * usr_cstr = clang_getCString(usr);
      if( std::strlen(usr_cstr) > 0 )
        xmlNewProp(cur_ptr, BAD_CAST "lex_parent_usr", BAD_CAST usr_cstr);
      clang_disposeString( usr );
    }

    CXCursor semanticParent = clang_getCursorSemanticParent(cursor);
    if( (!clang_Cursor_isNull(semanticParent)) &&
        (!clang_equalCursors(semanticParent, lexicalParent)) ) {
      CXString usr = clang_getCursorUSR(semanticParent);
      const char * usr_cstr = clang_getCString(usr);
      if( std::strlen(usr_cstr) > 0 )
        xmlNewProp(cur_ptr, BAD_CAST "sem_parent_usr", BAD_CAST usr_cstr);
      clang_disposeString( usr );
    }
  }

  // if( clang_isExpression(cursorKind) ) {
  //   xmlNewProp(cur_ptr, BAD_CAST "isExpr", BAD_CAST "True");
  // }
  // if( clang_isStatement(cursorKind) ) {
  //   xmlNewProp(cur_ptr, BAD_CAST "isStmt", BAD_CAST "True");
  // }
  // if( clang_isAttribute(cursorKind) ) {
  //   xmlNewProp(cur_ptr, BAD_CAST "isAttr", BAD_CAST "True");
  // }

  { 
    // Get referenced cursor
    CXCursor refc = clang_getCursorReferenced(cursor);
    if( (!clang_Cursor_isNull(refc)) &&
        (!clang_equalCursors(cursor, refc)) ) {
      CXString usr = clang_getCursorUSR(refc);
      const char * usr_cstr = clang_getCString(usr);
      if( std::strlen(usr_cstr) > 0 )
        xmlNewProp(cur_ptr, BAD_CAST "ref_usr", BAD_CAST usr_cstr);
      clang_disposeString( usr );
    }
   // Get definition cursor
    else {
      CXCursor defc = clang_getCursorDefinition(cursor);
      if( (!clang_Cursor_isNull(defc)) &&
          (!clang_equalCursors(cursor, defc)) ) {
        CXString usr = clang_getCursorUSR(defc);
      const char * usr_cstr = clang_getCString(usr);
      if( std::strlen(usr_cstr) > 0 )
        xmlNewProp(cur_ptr, BAD_CAST "def_usr", BAD_CAST usr_cstr);
      clang_disposeString( usr );
      }
    }
  }

  if( clang_isReference( cursorKind ) ) {
    xmlNewProp(cur_ptr, BAD_CAST "isRef", BAD_CAST "True");
  }

  if( clang_isDeclaration( cursorKind ) ) {
    xmlNewProp(cur_ptr, BAD_CAST "isDecl", BAD_CAST "True");

    // if( clang_isCursorDefinition( cursor ) ) {
    //   xmlNewProp(cur_ptr, BAD_CAST "isDef", BAD_CAST "True");
    // }

    // add access specifier
    CX_CXXAccessSpecifier ac_spec = clang_getCXXAccessSpecifier(cursor);
    const char * ac_spec_str;
    switch(ac_spec) {
      case CX_CXXPublic: ac_spec_str = "Public"; break;
      case CX_CXXProtected: ac_spec_str = "Protected"; break;
      case CX_CXXPrivate: ac_spec_str = "Private"; break;
      default: ac_spec_str = nullptr;
    };

    if( ac_spec_str != nullptr ) {
      xmlNewProp(cur_ptr, BAD_CAST "access_specifier", BAD_CAST ac_spec_str);
    }

    // add linkage kind
    CXLinkageKind linkage_kind = clang_getCursorLinkage(cursor);
    if( linkage_kind != CXLinkage_Invalid ) {
      const char * linkage_kind_str;
      switch(linkage_kind) {
        // automatic duration, no linking
        case CXLinkage_NoLinkage : linkage_kind_str = "auto"; break;
        // static linkage
        case CXLinkage_Internal  : linkage_kind_str = "internal"; break;
        // extern linkage for c++ anonymous namspaces
        case CXLinkage_UniqueExternal  : linkage_kind_str = "anon"; break;
        // true external linkage
        case CXLinkage_External : linkage_kind_str = "external"; break;
        // not possible
        default: linkage_kind_str = "none"; break;
      };
      xmlNewProp(cur_ptr, BAD_CAST "linkage_kind", BAD_CAST linkage_kind_str);
    }
  }

  clang_visitChildren( cursor, visitor, &nodeData );

  return CXChildVisit_Continue;
}

int main( int argc, char** argv ) {

  if( argc < 2 ) {
    fprintf(stderr, "Usage : %s <ast_file>\n", argv[0]);
    return -1;
  }

  CXIndex index        = clang_createIndex( 0, 1 );
  CXTranslationUnit tu = clang_createTranslationUnit( index, argv[1] );

  if( !tu ) {
    fprintf(stderr, "Error while reading / parsing %s\n", argv[1]);
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

  trav_data_t root_data{clang_getNullLocation(), root_node};

  clang_visitChildren(rootCursor, visitor, &root_data);

  /* Dump document to stdio or redirect to file */
  xmlSaveFormatFileEnc("-", doc, "UTF-8", 1);

  /* Free the document */
  xmlFreeDoc(doc);

  /* Free global variables that may have been allocated by libclang. */
  clang_disposeTranslationUnit( tu );
  clang_disposeIndex( index );

  /* Free the global variables that may have been allocated by the parser. */
  xmlCleanupParser();
  xmlMemoryDump();

  return 0;
}
