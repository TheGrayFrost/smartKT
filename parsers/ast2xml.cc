#include <clang-c/Index.h>
#include <iostream>
#include <fstream>
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
#define IDSIZE 11	 // normal unsigned int has 10 digits.. we are padding with one extra zero

/* 
	Notes about this code implementation:

	- LIBXML -
	1.	You can't just write any character in an xml as is. eg '<' has a special meaning and thus needs to be
		escaped as '&lt;' when passing to XML. In general, libxml handles this escaping by itself and we don't 
		have to worry about this.
	2.	A string in libxml is composed of the type xmlChar, which is a safer type than allowing all characters.
		Since our code works with C strings, which are based on char, we need to typecast to xmlChar before
		passing strings to libxml functions. libxml has the macro BAD_CAST used to convert char * to xmlChar * 
	
	- CLANG -
	1.	Reference to understand clang C/C++ tools recursive AST visitor:
		https://jonasdevlieghere.com/understanding-the-clang-ast/
		[API Reference: https://clang.llvm.org/doxygen/group__CINDEX.html]
		In short, we start from the clang AST root node, and traverse it depth-first. Calling the function
		clang_visitChildren(cursor, visitor, &nodeData) recursively.
	2.	Clang nodes are represented as CXCursor objects.
		In general, to add information about any clang node into xml we have to follow these steps:
		i. get that property fom the cursor eg: clang_getCursorType
		ii. get the clang internal string repr (CXString) of the property eg: clang_getCursorKindSpelling
		iii. convert CXString to C-format string using clang_getCString
		iv. add the property to the xml node using xmlNewProp(xml_node_ptr, BAD_CAST prop_name_cstring, 
		BAD_CAST prop_value_cstring);
		v. free the memory allocated for the C string representation clang_disposeString(CXString)
		(Note that you call disposeString on the CXString and not the C-style string)

	- CLANG NODE ID -
	1.	We create the clang node id by prepending the node's hash (found using clang_hashCursor) with a 
		file id passed to us. Node hashes are unique within any translation unit. Prepending it with file id
		makes it unique across all clang xml's generated. Refer to makeUniqueID() for implementation.
	2.	Clang node id's for the same node differ across multiple runs of the program. However, they are
		consistent for multiple AST traversals within a program. So, if we run this code twice, we shall
		get different ID's for the same nodes. But the different AST visitors, like get_call_expressions() and
		visitor() in this code, always see the same node ids within each run.
	
	- TEMPLATES -
	1.	Suppose you have a template function: template<typename T> f(T x), and you call f<int>(3);
		The clang node for this call would have a ref id pointing to the definition for f<int>()
		However, the source does not contain any such definition.
		So, clang creates a ghost (stub) node for this function definition of f<int>()
	2.	However, this ghost node is an orphan in the clang AST. So, the recursive AST visitor never reaches
		it. We keep a track of all the nodes we have seen. And when we see that any node has a ref_id, we
		have never encountered, we consider it a template specification, and emit it as a child of the
		TemplateStubs node (stub_root_node).

	- OVERALL STRUCTURE -
	We perform the ast2xml task in 4 steps:
	1.	Preprocessing Phase:
		- Run on the source cpp file.
		- Collects all nodes containing preprocessing information.
		- Done using: visitor() called with preprocessing_phase as True
	2.	Clang AST Phase:
		- Run on the .ast generated from the source cpp files.
		- The .ast is generated after preprocessor has run, so all macros have been expanded etc.
		- This is the main stage where we do all the things to handle templates etc.
		- Done using: visitor() called with preprocessing_phase as False
		- Important functions called in this phase
			i.	add_information: Adds all the relevant information about a clang node.
			ii.	add_function_information:
				- Called by add_information.
				- Adds extra type information for function declarations.
				- This type information is later used to generate .funcargs file
	3.	Template Collection Phase:
		- Run on the xml formed so far
		- It goes through all the def/ref cursors, that were not seen by visitor()
		- Adds information for them as a child of TemplateStubs node
	4.	Call Collection Phase:
		- Run on the .ast generated from the source cpp files.
		- Filters the call expressions, and emits info onto a .calls file
		- Done using: get_call_expressions()


	- Features currently under testing (DEBUG mode) -
		i. Adding storage class support
		ii. Adding visibility support
		iii. Checking extra nodes in Template Stubs
		iv. Testing static members and template functions inside template classes.
		v. Testing isAssignment for #define's
*/

std::string FILEID; // FILEID passed to ast2xml

CXTranslationUnit tu, source_tu; // declared global for accessing the source when needed
int preprocessing_phase;

inline bool operator == (const CXCursor & x, const CXCursor & y) {
	return clang_equalCursors(x, y) != 0;
}

// CXCursor hash required to create unordered set
namespace std {
	template<> struct hash<CXCursor>
	{
		inline size_t operator () (const CXCursor & cursor) const {
			return (size_t) clang_hashCursor(cursor);
		}
	};
}

// cursors_seen: what all clang AST nodes hae actually been visited
// stubs_seen: what all clang nodes have been referred to by others (using ref_id or def_id)
// used to later identify template stubs
std::unordered_set<CXCursor> cursors_seen, stubs_seen;

// clang output xml
xmlDocPtr doc = nullptr;
xmlNodePtr root_node = nullptr, stub_root_node = nullptr;

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
	return s.substr(0, res_ind);
}

// append file id to node id's to make them unique across all clang xmls generated
std::string makeUniqueID (unsigned id)
{
	// An unsigned int can have maximum 10 digits.
	// We convert it to a string of 11 chars by prepending zeros as required.
	// And then prepend the FILEID to that string
	std::string p = std::to_string(id);
	p = FILEID + std::string(IDSIZE - p.length(), '0') + p;
	return p;
}

// header for the .calls file generated
# define CALLS_FILEHEADER "# FILENAME\tLOCATION\tFUNCNAME\tCALLNODEID\n"

std::ofstream calls_file; // file where to write the call expressions

// Recursive visitor to track all function calls
CXChildVisitResult get_call_expressions
(CXCursor cursor, CXCursor parent, CXClientData) {

	static std::string const delim = "\t";

	CXCursorKind cursorKind = clang_getCursorKind(cursor);

	// Remove system headers' location
	CXSourceLocation location = clang_getCursorLocation(cursor);
	if (clang_Location_isInSystemHeader(location)) {
		return CXChildVisit_Continue;
	}

	// Filter call expressions
	if( cursorKind == CXCursor_CallExpr ) {
		CXCursor refc = clang_getCursorReferenced(cursor);
		if( !clang_Cursor_isNull(refc) ) {

			// Emit source filename & location.
			CXFile file;
			CXString fileName;
			unsigned line, column;

			clang_getSpellingLocation(location, &file, &line, &column, nullptr);
			fileName = clang_getFileName(file);
			calls_file << clang_getCString(fileName);
			
			CXSourceRange Range = clang_getCursorExtent(cursor);
			CXSourceLocation Rstart = clang_getRangeStart(Range);
			CXSourceLocation Rend = clang_getRangeEnd(Range);

			clang_getSpellingLocation(Rstart, nullptr, &line, &column, nullptr);
			calls_file << delim << line << ":" << column;
			clang_getSpellingLocation(Rend, nullptr, &line, &column, nullptr);
			calls_file << "::" << line << ":" << column;

			// Get linkage name and clang node id.
			CXString mangling = clang_Cursor_getMangling(refc);
			
			calls_file << delim << clang_getCString(mangling)
					<< delim << makeUniqueID(clang_hashCursor(cursor));

			calls_file << "\n";

			clang_disposeString(mangling);
			clang_disposeString( fileName );
		}
	}

	// Recursive visit call
	clang_visitChildren(cursor, get_call_expressions, nullptr);
	return CXChildVisit_Continue;
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

// Adds extra information for function declaration nodes
void add_function_information(CXCursor cursor, xmlNodePtr cur_ptr) {
	// Add linkage name
	CXString linkage_name = clang_Cursor_getMangling(cursor);
	xmlNewProp(cur_ptr, BAD_CAST "linkage_name", BAD_CAST clang_getCString(linkage_name));
	clang_disposeString(linkage_name);

	// Add return type
	CXType cursor_type = clang_getCursorType(cursor);
	CXString return_type = clang_getTypeSpelling(clang_getResultType(cursor_type));
	xmlNewProp(cur_ptr, BAD_CAST "return_type", BAD_CAST clang_getCString(return_type));
	clang_disposeString(return_type);

	// Add names of individual argument types.
	int nargs = clang_Cursor_getNumArguments(cursor);
	std::stringstream argstream;
	for(int i = 0; i < nargs; i++) {
		CXCursor arg_cursor = clang_Cursor_getArgument(cursor, i);
		CXType arg_type = clang_getCursorType(arg_cursor);
		CXString arg_type_spelling = clang_getTypeSpelling(arg_type);
		argstream << (i==0 ? "" : ",") << clang_getCString(arg_type_spelling);
		clang_disposeString(arg_type_spelling);
	}
	xmlNewProp(cur_ptr, BAD_CAST "funcargs", BAD_CAST argstream.str().c_str());
}

// Adds all the relevant info for a clang node
void add_information(CXCursor cursor, xmlNodePtr cur_ptr) {

	// Get the node type
	CXCursorKind cursorKind = clang_getCursorKind(cursor);

	// Call add_function_information for function declarations
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
	{
		CXFile file, par_file;
		CXString fileName;
		unsigned line, column, offset;
		clang_getSpellingLocation(location, &file, &line, &column, &offset);
		fileName = clang_getFileName(file);
		xmlNewProp(cur_ptr, BAD_CAST "file", BAD_CAST clang_getCString(fileName));
		clang_disposeString(fileName);
		xmlNewProp(cur_ptr, BAD_CAST "line", BAD_CAST std::to_string(line).c_str());
		xmlNewProp(cur_ptr, BAD_CAST "col", BAD_CAST std::to_string(column).c_str());
	}

	// Set cursor id
	std::string nodeid = makeUniqueID(clang_hashCursor(cursor));
	xmlNewProp(cur_ptr, BAD_CAST "id", BAD_CAST nodeid.c_str());

	{	// Set cursor spelling
		CXString spelling = clang_getCursorSpelling(cursor);
		const char* spelling_cstr = clang_getCString(spelling);
		if(std::strlen(spelling_cstr) > 0)
			xmlNewProp(cur_ptr, BAD_CAST "spelling", BAD_CAST spelling_cstr);
		clang_disposeString(spelling);
	}

	{	// Add USR if non empty
		CXString usr = clang_getCursorUSR(cursor);
		const char * usr_cstr = clang_getCString(usr);
		if(std::strlen(usr_cstr) > 0)
			xmlNewProp(cur_ptr, BAD_CAST "usr", BAD_CAST usr_cstr);
		clang_disposeString(usr);
	}


	{	// Add lexical / semantic parents
		CXCursor lexicalParent = clang_getCursorLexicalParent(cursor);
		if(!clang_Cursor_isNull(lexicalParent)) {
			std::string lexnodeid = makeUniqueID(clang_hashCursor(lexicalParent));
			xmlNewProp(cur_ptr, BAD_CAST "lex_parent_id", BAD_CAST lexnodeid.c_str());
		}

		CXCursor semanticParent = clang_getCursorSemanticParent(cursor);
		if((!clang_Cursor_isNull(semanticParent)) &&
				(!clang_equalCursors(semanticParent, lexicalParent))) {
			std::string semnodeid = makeUniqueID(clang_hashCursor(semanticParent));
			xmlNewProp(cur_ptr, BAD_CAST "sem_parent_id", BAD_CAST semnodeid.c_str());
		}
	}

	{	// Cursor type info
		CXType cursor_type = clang_getCursorType(cursor);
		CXString type_spelling = clang_getTypeSpelling(cursor_type);
		const char * type_spelling_cstr = clang_getCString(type_spelling);
		if(std::strlen(type_spelling_cstr) > 0) {
			xmlNewProp(cur_ptr, BAD_CAST "type", BAD_CAST type_spelling_cstr);
			// In current design type size is collected from dwarfdump
		}
		clang_disposeString(type_spelling);
	}

	{	// Add access specifier info - for inheritance and for class & struct vars
		// Clang gives both with same function clang_getCXXAccessSpecifier()
		// But we need to differentiate for our purpose
		CX_CXXAccessSpecifier ac_spec = clang_getCXXAccessSpecifier(cursor);
		const char * ac_spec_str;
		switch(ac_spec) {
			case CX_CXXPublic: ac_spec_str = "Public"; break;
			case CX_CXXProtected: ac_spec_str = "Protected"; break;
			case CX_CXXPrivate: ac_spec_str = "Private"; break;
			default: ac_spec_str = nullptr;
		};

		// If the cursor type is CXXBaseSpecifier, then we got the inheritance kind for a base class.
		const char * propKind;
		if (cursorKind == CXCursor_CXXBaseSpecifier) {
			propKind = "inheritance_kind";
			// Add info if that base class is virtual
			if (clang_isVirtualBase(cursor)) xmlNewProp(cur_ptr, BAD_CAST "isVirtualBase", BAD_CAST "True");
		}
		// Otherwise, it is the access specifier for a struct / class member
		else propKind = "access_specifier";

		// Add the access specifier info with correct property name
		if(ac_spec_str != nullptr) {
			xmlNewProp(cur_ptr, BAD_CAST propKind, BAD_CAST ac_spec_str);
		}
	}
	
	// add virtual information for CXX methods
	// Note: @Vishesh Do we need to consider virtual destructors separately??
	// Note: @Vishesh Do we need to consider static constructors separately??
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

	// Add info whether declaration. And other info related to declarations.
	if(clang_isDeclaration(cursorKind)) {
		xmlNewProp(cur_ptr, BAD_CAST "isDecl", BAD_CAST "True");

		// Get the linkage name for these people. This is required for readelf linking later.
		/* Imp. Note:
			Say, you have a function declaration f(int);
			Clang sets the argument 'int' to have isDecl true. In fact, it sets isDef also as true for it.
			But obviously, there is no name, it isn't even a declaration in the true sense.
			These "declarations", reasonably(?) give segfault we ask for mangled name.
			This check whether spelling exists saves us from that segfault.
		*/
		if (xmlGetProp(cur_ptr, BAD_CAST "spelling") != NULL)
		{
			CXString mangling = clang_Cursor_getMangling(cursor);
			std::string mangled(clang_getCString(mangling));
			if (mangled != "")
				xmlNewProp(cur_ptr, BAD_CAST "mangled_name", BAD_CAST mangled.c_str());
			clang_disposeString(mangling);
		}

		// If declaration is also definition.
		if(clang_isCursorDefinition(cursor)) {
			xmlNewProp(cur_ptr, BAD_CAST "isDef", BAD_CAST "True");
		}		

		// Add linkage kind
		CXLinkageKind linkage_kind = clang_getCursorLinkage(cursor);
		if(linkage_kind != CXLinkage_Invalid) {
			const char * linkage_kind_str;
			switch(linkage_kind) {
				// automatic duration, no linking
				case CXLinkage_NoLinkage : linkage_kind_str = "auto"; break;
				// static linkage
				case CXLinkage_Internal : linkage_kind_str = "internal"; break;
				// extern linkage for c++ anonymous namespaces
				case CXLinkage_UniqueExternal : linkage_kind_str = "anon"; break;
				// true external linkage
				case CXLinkage_External : linkage_kind_str = "external"; break;
				// not possible
				default: linkage_kind_str = "none"; break;
			};
			xmlNewProp(cur_ptr, BAD_CAST "linkage_kind", BAD_CAST linkage_kind_str);
		}
	}

	// Add cursor extent.
	CXSourceRange Range = clang_getCursorExtent(cursor);
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
	
	// Add whether an operator performs assignment
	// Note: Had to do it in such a roundabout way because libclang doesn't expose assignment op
	if (cursorKind == CXCursor_BinaryOperator) {
		CXToken* Tokens;
		unsigned NumTokens;

		// Go through the tokens and check whether any is "="
		// This might fail when the binary operator is in a #define
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
	// "+=" etc. also perform assignment
	else if (cursorKind == CXCursor_CompoundAssignOperator)
		xmlNewProp(cur_ptr, BAD_CAST "isAssignment", BAD_CAST "True");

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
					case CX_SC_Static	: storage_class_str = "static"; break;
					// register storage
					case CX_SC_Register	: storage_class_str = "register"; break;
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
	}

}


// Recursive visitor to DFS on AST and collect information into XML
CXChildVisitResult
visitor(CXCursor cursor, CXCursor, CXClientData clientData) {

	// Get the parent's XML node
	auto parentNode = * (reinterpret_cast<xmlNodePtr *>(clientData));

	// Add cursor to cursors_seen
	// Ignore if already seen. This can happen if a node has two parents.
	if(!cursors_seen.insert(cursor).second) {
		return CXChildVisit_Continue;
	}

	// Remove system headers' location
	CXSourceLocation location = clang_getCursorLocation(cursor);
	if (clang_Location_isInSystemHeader(location)) {
		return CXChildVisit_Continue;
	}

	// Get cursor kind
	CXCursorKind cursorKind = clang_getCursorKind(cursor);

	// If in preprocessing phase, only collect preprocessing nodes (include directives etc.)
	if (preprocessing_phase && ! clang_isPreprocessing(cursorKind)) {
		return CXChildVisit_Continue;
	}

	// Create the current XML node with cursor kind as the node tag
	CXString kindName = clang_getCursorKindSpelling(cursorKind);
	std::string xmlNodeName(clang_getCString(kindName));
	xmlNodePtr cur_ptr = xmlNewChild(parentNode, nullptr, 
	BAD_CAST camelCaseSanitize(xmlNodeName).c_str(), nullptr);	
	clang_disposeString(kindName);

	{	// Get definition / reference cursor
		// Keep track of referred cursors in stubs_seen
		CXCursor defc = clang_getCursorDefinition(cursor);
		if((!clang_Cursor_isNull(defc)) && (!clang_equalCursors(cursor, defc))) {
			std::string defnodeid = makeUniqueID(clang_hashCursor(defc));
			xmlNewProp(cur_ptr, BAD_CAST "def_id", BAD_CAST defnodeid.c_str());
			stubs_seen.insert(defc);
		}
		else {
			CXCursor refc = clang_getCursorReferenced(cursor);
			if((!clang_Cursor_isNull(refc)) && (!clang_equalCursors(cursor, refc))) {
				std::string refnodeid = makeUniqueID(clang_hashCursor(refc));
				xmlNewProp(cur_ptr, BAD_CAST "ref_id", BAD_CAST refnodeid.c_str());
				stubs_seen.insert(refc);
			}
		}
	}

	// Add all other information about this cursor
	add_information(cursor, cur_ptr);

	// Do the recursive visit
	clang_visitChildren(cursor, visitor, &cur_ptr);

	return CXChildVisit_Continue;
}

void add_stub_nodes() {
	// For all the referenced cursors
	for(CXCursor stub: stubs_seen) {
		// If they have been seen by visitor before, continue
		if(cursors_seen.find(stub) != cursors_seen.end())
			continue;

		// Otherwise, add it as a child of stub_root_node
		CXCursorKind stubCursorKind = clang_getCursorKind(stub);
		CXString stubKindName = clang_getCursorKindSpelling(stubCursorKind);
		std::string stubNodeName(clang_getCString(stubKindName));
		xmlNodePtr stub_ptr = xmlNewChild(stub_root_node, nullptr,
				BAD_CAST camelCaseSanitize(stubNodeName).c_str(), nullptr);

		{	// Add definition / reference cursor
			CXCursor defc = clang_getCursorDefinition(stub);
			if((!clang_Cursor_isNull(defc)) && (!clang_equalCursors(stub, defc))) {
				std::string defnodeid = makeUniqueID(clang_hashCursor(defc));
				xmlNewProp(stub_ptr, BAD_CAST "def_id", BAD_CAST defnodeid.c_str());
			}
			else {
				CXCursor refc = clang_getCursorReferenced(stub);
				if((!clang_Cursor_isNull(refc)) && (!clang_equalCursors(stub, refc))) {
					std::string refnodeid = makeUniqueID(clang_hashCursor(refc));
					xmlNewProp(stub_ptr, BAD_CAST "ref_id", BAD_CAST refnodeid.c_str());
				}
			}
		}

		// Add all other information about this cursor
		add_information(stub, stub_ptr);

		{	// Get the node whose template specialization this guy is
			CXCursor spt = clang_getSpecializedCursorTemplate(stub);
			if(! clang_Cursor_isNull(spt)) {
				std::string tempnodeid = makeUniqueID(clang_hashCursor(spt));
				xmlNewProp(stub_ptr, BAD_CAST "ref_tmp", BAD_CAST tempnodeid.c_str());
			}
		}
	}
}


int main( int argc, char** argv ) {

	if( argc != 6 ) {
		fprintf(stderr, "Usage : %s <file_num> <source_file> <ast_file> <calls_file> <xml_file>\n", argv[0]);
		return -1;
	}

	/* liblang and libxml initializations */

	FILEID = std::string(argv[1]);
	CXIndex index = clang_createIndex(0, 0);
	LIBXML_TEST_VERSION;
	doc = xmlNewDoc(BAD_CAST "1.0"); // Create a new XML document
	xmlCreateIntSubset(doc, BAD_CAST "TranslationUnit", nullptr, BAD_CAST "smartkt.dtd");
	// Get root element TranslationUnit for XML doc
	root_node = xmlNewNode(nullptr, BAD_CAST "TranslationUnit");
	xmlDocSetRootElement(doc, root_node);
	// Add TemplateStubs as child of root
	stub_root_node = xmlNewChild(root_node, nullptr, BAD_CAST "TemplateStubs", nullptr);


	/* 1. Preprcessing Phase */

	// Parse the source file and the get the root cursor
	source_tu = clang_parseTranslationUnit(index, argv[2],
			0, 0, 0, 0, CXTranslationUnit_DetailedPreprocessingRecord);
	if( !source_tu ) {
		fprintf(stderr, "Error while reading / parsing %s\n", argv[2]);
		return -1;
	}
	CXCursor source_root_cursor = clang_getTranslationUnitCursor( source_tu );

	// set the preprocessing_phase make the recursive visit call
	preprocessing_phase = 1;
	clang_visitChildren(source_root_cursor, visitor, &root_node);


	/* 2. Clang AST Phase */

	// Parse the ast file and the get the root cursor
	tu = clang_createTranslationUnit(index, argv[3]);
	if(!tu) {
		fprintf(stderr, "Error while reading / parsing %s\n", argv[3]);
		return -1;
	}
	CXCursor root_cursor = clang_getTranslationUnitCursor(tu);

	// unset the preprocessing_phase make the recursive visit call
	preprocessing_phase = 0;
	clang_visitChildren(root_cursor, visitor, &root_node);
	

	/* 3. Template Collection Phase */
	add_stub_nodes();


	/* 4. Call Collection Phase */
	calls_file.open(argv[4]);
	calls_file << CALLS_FILEHEADER;
	clang_visitChildren(root_cursor, get_call_expressions, nullptr);
	calls_file.close();


	/* liblang and libxml cleanup */
	
	// Write the XML doc
	xmlSaveFormatFileEnc(argv[5], doc, "UTF-8", 1);
	// Dealloc libxml resources
	xmlFreeDoc(doc);
	xmlCleanupParser();
	xmlMemoryDump();

	// Free global variables that may have been allocated by libclang
	clang_disposeTranslationUnit( source_tu );
	clang_disposeTranslationUnit( tu );
	clang_disposeIndex( index );

	return 0;
}
