#include <clang-c/Index.h>
#include <iostream>
#include <sstream>
#include <unordered_set>

#include <libxml/parser.h>
#include <libxml/tree.h>

#include <algorithm>
#include <string>
#include <cstring>
#include <cstdlib>

#include "ctype.h"

#define DEBUG true

#define IDSIZE 11   // normal unsigned int has 10 digits.. we are padding with one extra zero
std::string FILEID; // FILEID passed to ast2xml

CXTranslationUnit tu; // declared global for accessing the source when needed

inline bool operator==(const CXCursor & x, const CXCursor & y) {
    return clang_equalCursors(x, y) != 0;
}

namespace std {
	template<> struct hash<CXCursor>
	{
    inline size_t operator()(const CXCursor & cursor) const {
		  return (size_t) clang_hashCursor(cursor);
    }
	};
}

std::unordered_set<CXCursor> cursors_seen, stubs_seen;

xmlDocPtr doc = nullptr;
xmlNodePtr root_node = nullptr, stub_root_node = nullptr;

struct trav_data_t {
  CXSourceLocation cur_loc; // Location of current cursor.
  xmlNodePtr xml_ptr; // XML node corresponding to current cursor.
};

// makes strings safe for xml consumption
std::string camelCaseSanitize(std::string s){
  int n = s.length(), res_ind = 0;
  for(int i=0; i<n; i++){
    if(s[i] == ' ') { s[i+1] = std::toupper(s[i+1]); continue; }
    else {
      if(s[i] == '+') s[i] = 'X';
      else if (s[i] == '(' || s[i] == ')') s[i] = '_';
      s[res_ind++] = s[i];
    }
  }
  // std::replace(s.begin(), s.end(), ' ', '_');
  // std::replace(s.begin(), s.end(), '(', '_');
  // std::replace(s.begin(), s.end(), ')', '_');
  // std::replace(s.begin(), s.end(), '+', 'X');
  return s.substr(0, res_ind);
}

std::string makeUniqueID (unsigned id)
{
  std::string p = std::to_string(id);
  p = FILEID + std::string(IDSIZE - p.length(), '0') + p;
  return p;
}

// prints tokenwise information about a cursor
// used for debugging
std::string cursorInspect (CXCursor& cursor) {
  CXSourceRange Range = clang_getCursorExtent(cursor);
  CXToken* Tokens;
  unsigned NumTokens;
  std::string clause;

  clang_tokenize(tu, Range, &Tokens, &NumTokens);
  for (unsigned i = 0; i < NumTokens; ++i) {
    // get the token
    CXTokenKind tkind = clang_getTokenKind(Tokens[i]);
    CXString curtok = clang_getTokenSpelling(tu, Tokens[i]);
    clause += std::string(clang_getCString(curtok)) + "@";
    clang_disposeString(curtok);

    // get corresponding cursor kind
    CXCursor u = clang_getCursor(tu, clang_getTokenLocation(tu, Tokens[i]));
    CXCursorKind tKind = clang_getCursorKind(u);
    CXString tkindName = clang_getCursorKindSpelling(tKind);
    clause += std::string(clang_getCString(tkindName)) + " ";
    clang_disposeString(tkindName);
  }
  clang_disposeTokens(tu, Tokens, NumTokens);

  return clause;
}


void add_function_information(CXCursor cursor, xmlNodePtr cur_ptr) {
    /* Emit generic function data. */
    CXString linkage_name = clang_Cursor_getMangling(cursor);
    xmlNewProp(cur_ptr, BAD_CAST "linkage_name", BAD_CAST clang_getCString(linkage_name));
    clang_disposeString(linkage_name);

    CXType cursor_type = clang_getCursorType(cursor);
    CXString return_type = clang_getTypeSpelling(clang_getResultType(cursor_type));
    xmlNewProp(cur_ptr, BAD_CAST "return_type", BAD_CAST clang_getCString(return_type));
    clang_disposeString(return_type);

    // Names of individual argument types included in display_name.
    int nargs = clang_Cursor_getNumArguments(cursor);
    std::stringstream argstream;
    for(int i = 0; i < nargs; i++) {
        CXCursor arg_cursor = clang_Cursor_getArgument(cursor, i);
        CXType arg_type = clang_getCursorType(arg_cursor);
        CXString arg_type_spelling = clang_getTypeSpelling(arg_type);
        argstream << (i==0 ? "" : ",") << clang_getCString(arg_type_spelling) ;
        clang_disposeString(arg_type_spelling);
    }

    xmlNewProp(cur_ptr, BAD_CAST "funcargs", BAD_CAST argstream.str().c_str());
}

void add_information(CXCursor cursor, xmlNodePtr cur_ptr) {
  CXCursorKind cursorKind = clang_getCursorKind(cursor);

  switch(cursorKind) {
    case CXCursor_Constructor :
    case CXCursor_Destructor :
    case CXCursor_CXXMethod :
    case CXCursor_FunctionDecl :
      add_function_information(cursor, cur_ptr);
    default: ;
  }

  CXSourceLocation location = clang_getCursorLocation(cursor);

  // Add location info.
  // if(! clang_equalLocations(parentData->cur_loc, location)) {
  {
    CXFile file, par_file;
    CXString fileName;
    unsigned line, column, offset;
    clang_getSpellingLocation(location, &file, &line, &column, &offset);
    // clang_getSpellingLocation(parentData->cur_loc,
    //   &par_file, nullptr, nullptr, nullptr);
    // if(! clang_File_isEqual(par_file, file)) {
    {
      fileName = clang_getFileName(file);
      xmlNewProp(cur_ptr, BAD_CAST "file", BAD_CAST clang_getCString(fileName));
      clang_disposeString(fileName);
    }
    xmlNewProp(cur_ptr, BAD_CAST "line", BAD_CAST std::to_string(line).c_str());
    xmlNewProp(cur_ptr, BAD_CAST "col", BAD_CAST std::to_string(column).c_str());
    // xmlNewProp(cur_ptr, BAD_CAST "off", BAD_CAST std::to_string(offset).c_str());
  }

  // set cursor id
  std::string nodeid = makeUniqueID(clang_hashCursor(cursor));
  xmlNewProp(cur_ptr, BAD_CAST "id", BAD_CAST nodeid.c_str());

  // set cursor spelling
  {
    CXString spelling = clang_getCursorSpelling(cursor);
    const char* spelling_cstr = clang_getCString(spelling);
    if(std::strlen(spelling_cstr) > 0)
      xmlNewProp(cur_ptr, BAD_CAST "spelling", BAD_CAST spelling_cstr);
    clang_disposeString(spelling);
  }

  { // Add USR if non empty
    CXString usr = clang_getCursorUSR(cursor);
    const char * usr_cstr = clang_getCString(usr);
    if(std::strlen(usr_cstr) > 0)
      xmlNewProp(cur_ptr, BAD_CAST "usr", BAD_CAST usr_cstr);
    clang_disposeString(usr);
  }


  // Mangled name has been shifted to Dwarfdump

  { // Add lexical / semantic parents
    CXCursor lexicalParent = clang_getCursorLexicalParent(cursor);
    if(!clang_Cursor_isNull(lexicalParent)) {
      std::string lexnodeid = makeUniqueID(clang_hashCursor(lexicalParent));
      xmlNewProp(cur_ptr, BAD_CAST "lex_parent_id", BAD_CAST lexnodeid.c_str());
      // CXString usr = clang_getCursorUSR(lexicalParent);
      // const char * usr_cstr = clang_getCString(usr);
      // if(std::strlen(usr_cstr) > 0)
      //   xmlNewProp(cur_ptr, BAD_CAST "lex_parent_usr", BAD_CAST usr_cstr);
      // clang_disposeString(usr);
    }

    CXCursor semanticParent = clang_getCursorSemanticParent(cursor);
    if((!clang_Cursor_isNull(semanticParent)) &&
        (!clang_equalCursors(semanticParent, lexicalParent))) {
      std::string semnodeid = makeUniqueID(clang_hashCursor(semanticParent));
      xmlNewProp(cur_ptr, BAD_CAST "sem_parent_id", BAD_CAST semnodeid.c_str());
      // CXString usr = clang_getCursorUSR(semanticParent);
      // const char * usr_cstr = clang_getCString(usr);
      // if(std::strlen(usr_cstr) > 0)
      //   xmlNewProp(cur_ptr, BAD_CAST "sem_parent_usr", BAD_CAST usr_cstr);
      // clang_disposeString(usr);
    }
  }

  // Cursor type info
  {
    CXType cursor_type = clang_getCursorType(cursor);
    CXString type_spelling = clang_getTypeSpelling(cursor_type);
    const char * type_spelling_cstr = clang_getCString(type_spelling);
    if(std::strlen(type_spelling_cstr) > 0) {
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
    clang_disposeString(type_spelling);
  }

  // add access specifier - for inheritance and for class & struct vars
  {
    CX_CXXAccessSpecifier ac_spec = clang_getCXXAccessSpecifier(cursor);
    const char * ac_spec_str;
    switch(ac_spec) {
      case CX_CXXPublic: ac_spec_str = "Public"; break;
      case CX_CXXProtected: ac_spec_str = "Protected"; break;
      case CX_CXXPrivate: ac_spec_str = "Private"; break;
      default: ac_spec_str = nullptr;
    };

    const char * propKind;
    if (cursorKind == CXCursor_CXXBaseSpecifier) {
        propKind = "inheritance_kind";
        if (clang_isVirtualBase(cursor)) xmlNewProp(cur_ptr, BAD_CAST "isVirtualBase", BAD_CAST "True");
    }
    else propKind = "access_specifier";

    if(ac_spec_str != nullptr) {
      xmlNewProp(cur_ptr, BAD_CAST propKind, BAD_CAST ac_spec_str);
    }
  }
  
  // add virtual information for CXX methods 
  // Note: @Vishesh Do we need to consider virtual destructors as well??
  // Note: @Vishesh Do we need to consider static constructors as well??
  if (cursorKind == CXCursor_CXXMethod){
    if (clang_CXXMethod_isPureVirtual(cursor)) {
    xmlNewProp(cur_ptr, BAD_CAST "isCXXPureVirtual", BAD_CAST "True");
    }
    else if (clang_CXXMethod_isVirtual(cursor)) {
      xmlNewProp(cur_ptr, BAD_CAST "isCXXVirtual", BAD_CAST "True");
    }
    else if (clang_CXXMethod_isStatic(cursor)) {
      xmlNewProp(cur_ptr, BAD_CAST "isCXXStatic", BAD_CAST "True");
    }
  }

  if(clang_isReference(cursorKind)) {
    xmlNewProp(cur_ptr, BAD_CAST "isRef", BAD_CAST "True");
  }

  if(clang_isDeclaration(cursorKind)) {
    xmlNewProp(cur_ptr, BAD_CAST "isDecl", BAD_CAST "True");

    if(clang_isCursorDefinition(cursor)) {
      xmlNewProp(cur_ptr, BAD_CAST "isDef", BAD_CAST "True");
    }    

    // add linkage kind
    CXLinkageKind linkage_kind = clang_getCursorLinkage(cursor);
    if(linkage_kind != CXLinkage_Invalid) {
      const char * linkage_kind_str;
      switch(linkage_kind) {
        // automatic duration, no linking
        case CXLinkage_NoLinkage : linkage_kind_str = "auto"; break;
        // static linkage
        case CXLinkage_Internal  : linkage_kind_str = "internal"; break;
        // extern linkage for c++ anonymous namespaces
        case CXLinkage_UniqueExternal  : linkage_kind_str = "anon"; break;
        // true external linkage
        case CXLinkage_External : linkage_kind_str = "external"; break;
        // not possible
        default: linkage_kind_str = "none"; break;
      };
      xmlNewProp(cur_ptr, BAD_CAST "linkage_kind", BAD_CAST linkage_kind_str);
    }
  }

  CXSourceRange Range = clang_getCursorExtent(cursor);
  // Add cursor extent.
  {
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
  
  // add whether binary operator is assignment
  // Note: @Vishesh Had to do it in such a roundabout way because libclang doesn't expose
  if (cursorKind == CXCursor_BinaryOperator) {
    CXToken* Tokens;
    unsigned NumTokens;

    clang_tokenize(tu, Range, &Tokens, &NumTokens);
    for (unsigned i = 0; i < NumTokens; ++i) {
      CXTokenKind tkind = clang_getTokenKind(Tokens[i]);
      
      if (clang_hashCursor(cursor) == clang_hashCursor(
                clang_getCursor(tu, clang_getTokenLocation(tu, Tokens[i])))) {
        CXString curtok = clang_getTokenSpelling(tu, Tokens[i]);
        if (std::string(clang_getCString(curtok)) == "=")
          xmlNewProp(cur_ptr, BAD_CAST "isAssignment", BAD_CAST "True");
        clang_disposeString(curtok);
        break;
      }
    }
    clang_disposeTokens(tu, Tokens, NumTokens);
  }
  else if (cursorKind == CXCursor_CompoundAssignOperator)
    xmlNewProp(cur_ptr, BAD_CAST "isAssignment", BAD_CAST "True");

  // // add inheritance information for classes
  // // Note: @Vishesh Had to do it in such a hacky way because libclang is somehow v v wrong
  // if (cursorKind == CXCursor_CXXBaseSpecifier) {
  //   CXToken* Tokens;
  //   unsigned NumTokens;
    
  //   clang_tokenize(tu, Range, &Tokens, &NumTokens);
  //   CX_CXXAccessSpecifier itype = CX_CXXPrivate;
  //   for (unsigned i = 0; i < NumTokens; ++i) {
  //     CXString curtok = clang_getTokenSpelling(tu, Tokens[i]);
  //     std::string tokspell(clang_getCString(curtok));
  //     if (tokspell == "public") itype = CX_CXXPublic;
  //     else if (tokspell == "protected")itype = CX_CXXProtected;
  //     // default is private
  //     clang_disposeString(curtok);
  //   }
  //   const char * ac_spec_str;
  //   switch(itype) {
  //     case CX_CXXPublic: ac_spec_str = "Public"; break;
  //     case CX_CXXProtected: ac_spec_str = "Protected"; break;
  //     case CX_CXXPrivate: ac_spec_str = "Private"; break;
  //   };
  //   clang_disposeTokens(tu, Tokens, NumTokens);

  //   xmlNewProp(cur_ptr, BAD_CAST "inheritance_kind", BAD_CAST ac_spec_str);
    
  //   if (clang_isVirtualBase(cursor)) {
  //     xmlNewProp(cur_ptr, BAD_CAST "isVirtualBase", BAD_CAST "True");
  //   }
    
  // }

  // features currently under test
  if (DEBUG) {
    {
      // add storage class - discarded since stupid clang gives auto storage for globals as well
      // will have to use combined criteria (auto storage + external linkage)

      // also CX_SC_PrivateExtern should be a linkage thing... it is basically hidden visibility
      // i.e. objects only visible within one shared object, and nowhere outside

      CX_StorageClass storage_class = clang_Cursor_getStorageClass(cursor);
      if(storage_class != CX_SC_Invalid) {
        const char * storage_class_str;
        switch(storage_class) {
          // automatic storage duration
          case CX_SC_Auto: storage_class_str = "clang_auto"; break;
          case CX_SC_None : storage_class_str = "default_auto"; break;
          // static storage
          case CX_SC_PrivateExtern: storage_class_str = "private_extern"; break;
          case CX_SC_Static  : storage_class_str = "static"; break;
          // register storage
          case CX_SC_Register  : storage_class_str = "register"; break;
          // not really sure what this means
          case CX_SC_Extern : storage_class_str = "extern"; break;
          // not possible
          default: storage_class_str = "none"; break;
        };
        xmlNewProp(cur_ptr, BAD_CAST "storage_class", BAD_CAST storage_class_str);
      }
    }

    {
      // visibility
      CXVisibilityKind visibility = clang_getCursorVisibility(cursor);
      if(visibility != CXVisibility_Invalid) {
        const char * visi_str;
        switch(visibility) {
          // automatic storage duration
          case CXVisibility_Hidden: visi_str = "hidden"; break;
          case CXVisibility_Protected : visi_str = "protected"; break;
          case CXVisibility_Default : visi_str = "default"; break;
          default: visi_str = "none"; break;
        };
        xmlNewProp(cur_ptr, BAD_CAST "visibility", BAD_CAST visi_str);
      }
    }

    if(clang_isDeclaration(cursorKind)) {
      CXString display = clang_getCursorDisplayName(cursor);
      const char * display_name = clang_getCString(display);
      if(std::strlen(display_name) > 0)
        xmlNewProp(cur_ptr, BAD_CAST "display_name", BAD_CAST display_name);
      clang_disposeString(display);
    }

    // && !(clang_isCursorDefinition(cursor) && cursorKind !=))
    // if(clang_isDeclaration(cursorKind)) {
    //   CXPrintingPolicy policy = clang_getCursorPrintingPolicy(cursor);
    //   clang_PrintingPolicy_setProperty(policy, CXPrintingPolicy_IncludeTagDefinition, false);
    //   clang_PrintingPolicy_setProperty(policy, CXPrintingPolicy_FullyQualifiedName, true);
    //   clang_PrintingPolicy_setProperty(policy, CXPrintingPolicy_SuppressInitializers, false);
      
    //   CXString pretty = clang_getCursorPrettyPrinted(cursor, policy);
    //   const char * pretty_name = clang_getCString(pretty);
    //   if(std::strlen(pretty_name) > 0)
    //     xmlNewProp(cur_ptr, BAD_CAST "pretty_name", BAD_CAST pretty_name);
    //   clang_disposeString(pretty);
    //   clang_PrintingPolicy_dispose(policy);
    // }
  }

}


// Recursive visitor to DFS on AST and collect information into XML
CXChildVisitResult
visitor(CXCursor cursor, CXCursor, CXClientData clientData) {
  auto parentData = (reinterpret_cast<trav_data_t*>(clientData));

  if(!cursors_seen.insert(cursor).second) {
    return CXChildVisit_Continue;
  }

  // Remove system headers' location
  CXSourceLocation location = clang_getCursorLocation(cursor);
  if (clang_Location_isInSystemHeader(location)) {
  	return CXChildVisit_Continue;
  }

  CXCursorKind cursorKind = clang_getCursorKind(cursor);
  CXString kindName = clang_getCursorKindSpelling(cursorKind);
  std::string xmlNodeName(clang_getCString(kindName));
  
  xmlNodePtr cur_ptr = xmlNewChild(parentData->xml_ptr, nullptr, 
    BAD_CAST camelCaseSanitize(xmlNodeName).c_str(), nullptr);  
  clang_disposeString(kindName);

  trav_data_t nodeData{clang_getNullLocation(), cur_ptr};
  nodeData.cur_loc = clang_getCursorLocation(cursor);

  // Linkage, if found within the file
  {
    // Get definition cursor
    CXCursor defc = clang_getCursorDefinition(cursor);
    if((!clang_Cursor_isNull(defc)) &&
        (!clang_equalCursors(cursor, defc))) {
      std::string defnodeid = makeUniqueID(clang_hashCursor(defc));
      xmlNewProp(cur_ptr, BAD_CAST "def_id", BAD_CAST defnodeid.c_str());

      stubs_seen.insert(defc);
    }
   
    // Otherwise, get referenced cursor
    else {
      CXCursor refc = clang_getCursorReferenced(cursor);
      if((!clang_Cursor_isNull(refc)) &&
          (!clang_equalCursors(cursor, refc))) {
        std::string refnodeid = makeUniqueID(clang_hashCursor(refc));
        xmlNewProp(cur_ptr, BAD_CAST "ref_id", BAD_CAST refnodeid.c_str());

        stubs_seen.insert(refc);
      }
    }
  }

  add_information(cursor, cur_ptr);

  clang_visitChildren(cursor, visitor, &nodeData);

  return CXChildVisit_Continue;
}

void add_stub_nodes() {
    for(CXCursor stub: stubs_seen) {
        if(cursors_seen.find(stub) != cursors_seen.end())
            continue;

        CXCursorKind stubCursorKind = clang_getCursorKind(stub);
        CXString stubKindName = clang_getCursorKindSpelling(stubCursorKind);
        std::string stubNodeName(clang_getCString(stubKindName));

        xmlNodePtr stub_ptr = xmlNewChild(stub_root_node, nullptr,
            BAD_CAST camelCaseSanitize(stubNodeName).c_str(), nullptr);

        add_information(stub, stub_ptr);

        CXCursor defc = clang_getCursorDefinition(stub);
        if((!clang_Cursor_isNull(defc)) &&
            (!clang_equalCursors(stub, defc))) {
            std::string defnodeid = makeUniqueID(clang_hashCursor(defc));
            xmlNewProp(stub_ptr, BAD_CAST "def_id", BAD_CAST defnodeid.c_str());
        } else {
           CXCursor refc = clang_getCursorReferenced(stub);
           if((!clang_Cursor_isNull(refc)) &&
                (!clang_equalCursors(stub, refc))) {
                std::string refnodeid = makeUniqueID(clang_hashCursor(refc));
                xmlNewProp(stub_ptr, BAD_CAST "ref_id", BAD_CAST refnodeid.c_str());
            }
        }

        CXCursor spt = clang_getSpecializedCursorTemplate(stub);
        if(! clang_Cursor_isNull(spt)) {
            std::string tempnodeid = makeUniqueID(clang_hashCursor(spt));
            xmlNewProp(stub_ptr, BAD_CAST "ref_tmp", BAD_CAST tempnodeid.c_str());
        }
    }
}

int main(int argc, char** argv) {

  if(argc < 3) {
    fprintf(stderr, "Usage : %s <file_num> <ast_file>\n", argv[0]);
    return -1;
  }

  FILEID = std::string(argv[1]);

  CXIndex index = clang_createIndex(0, 1);
  tu = clang_createTranslationUnit(index, argv[2]);

  if(!tu) {
    fprintf(stderr, "Error while reading / parsing %s\n", argv[2]);
    return -1;
  }

  LIBXML_TEST_VERSION;

  /* Creates a new document, a node and set it as a root node */
  doc = xmlNewDoc(BAD_CAST "1.0");
  root_node = xmlNewNode(nullptr, BAD_CAST "TranslationUnit");
  xmlDocSetRootElement(doc, root_node);

  stub_root_node = xmlNewChild(root_node, nullptr, BAD_CAST "TemplateStubs", nullptr);

  /* Creates a DTD declaration. Isn't mandatory. */
  xmlCreateIntSubset(doc, BAD_CAST "TranslationUnit",
    nullptr, BAD_CAST "smartkt.dtd");

  /* Get root cursor. */
  CXCursor rootCursor  = clang_getTranslationUnitCursor(tu);

  trav_data_t root_data{clang_getNullLocation(), root_node};

  clang_visitChildren(rootCursor, visitor, &root_data);
  add_stub_nodes();

  /* Dump document to stdio or redirect to file */
  xmlSaveFormatFileEnc("-", doc, "UTF-8", 1);

  /* Free the document */
  xmlFreeDoc(doc);

  /* Free global variables that may have been allocated by libclang. */
  clang_disposeTranslationUnit(tu);
  clang_disposeIndex(index);

  /* Free the global variables that may have been allocated by the parser. */
  xmlCleanupParser();
  xmlMemoryDump();

  return 0;
}
