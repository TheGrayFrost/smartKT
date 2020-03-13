// #include <unistd.h>
// #include <sys/wait.h>
#include "memtracker.h"
#include <map>
#include <algorithm>
#include <fstream>
#include <iterator>
#include <set>
#include <cstdlib>

#define DEBUG false
#define VARSEARCH false

// parse with new header
// emit with new header
// id -> ts


// major things left to do:
// 1. making lock_func_af work using IPOINT_BEFORE on return
// 2. tracing mallocs
// 3. tracing non-primitive return values and call arguments

PIN_LOCK globalLock;

std::string folder = "statinfo/";
std::string foff = "final.offset";
std::string faddr = ".address";
std::string fargs = "final.funcargs";
std::string fcalls = "final.calls";


std::map <std::string, int> locks;		// mutex -> type
std::map <int, std::string> unlocks;	// type -> mutex name

std::ofstream outp;						// file to write to

// should do routine wise for memory efficiency
std::map <ADDRINT, INSINFO> inslist;					// all instructions

std::map <THREADID, std::map<ADDRINT, int>> syncs;		// thread -> lock address -> mutex type

long long int timeStamp = 0;			// global event timestep

std::map <std::string, std::map<THREADID, int>> invMap;	// function invocation number


struct fnlog
{
	THREADID tid;
	std::string fname;
	// std::string filename;
	int invNo;
	ADDRINT rbp;

	fnlog() {;}
	fnlog (std::string fn, THREADID t, ADDRINT bp) {fname = fn, tid = t, invNo = invMap[fn][t]; rbp = bp;}
	fnlog (std::string fn, THREADID t, int ino, ADDRINT bp) {fname = fn, tid = t, invNo = ino; rbp = bp;}
	void print(std::ostream& outf = std::cout) const {outf << "|" << tid << ":" << fname << ":" << invNo << ":" << rbp << "| ";}
	bool operator < (const fnlog& rhs) const
	{
		if (tid != rhs.tid) return tid < rhs.tid;
		if (fname != rhs.fname) return fname < rhs.fname;
		return invNo < rhs.invNo;
	}
};

std::map <ADDRINT, fnlog> RBPstack;
// std::map <fnlog, ADDRINT> fnstack;
std::map <THREADID, std::vector <fnlog>> invstack;


void printRBP (std::ostream& outf = std::cout)
{
	outf << "\n\nRBPSTACK\n\n";
	for (auto i: RBPstack)
	{
		outf << i.first << "->";
		i.second.print(outf);
	}
	outf << "\n\n";
}

// void printfn (std::ostream& outf = std::cout)
// {
// 	outf << "\n\nFNSTACK\n\n";
// 	for (auto i: fnstack)
// 	{
// 		i.first.print(outp);
// 		outf << "->" << i.second << " ";
// 	}
// 	outf << "\n\n";
// }

void printinv (std::ostream& outf = std::cout)
{
	outf << "\n\nINVSTACK\n\n";
	for (auto i: invstack)
	{
		outf << i.first << ": ";
		for (auto j: i.second)
			j.print(outf);
			outf << " -> ";
		outf << "\n";
	}
	outf << "\n\n";
}

void printall()
{
	printRBP(outp);
	// printfn(outp);
	printinv(outp);
}

// std::map <THREADID, std::vector <ADDRINT>> RBPstack;
// std::map <THREADID, std::vector <std::string>> fnstack;

struct variable
{
	std::string name;	// variable name
	std::string id;		// clang node id
	ssize_t size;		// size (needed for structs, classes)
	std::string fname;	// variable container
	std::string type;	// variable type
	std::string pid;	// variable semantic parent id
	std::string spattr;	// special attribute: storage class type

	int nElem;			// number of elements if array
	bool isPtr;			// if it has pointer type

	void print(std::ostream& outf = std::cout) 
	{
		outf << fname << ": " << type << " - " << name << ": " << id << " " 
			<< spattr << " " << (((signed)(spattr.find("STATIC")) > 0)?fname:"") 
			<< " Ptr: " << isPtr << " nEl: " << nElem << "\n";
	}
	void patch()
	{
		isPtr = false;
		if (type.find("*") != -1)
			isPtr = true;
		nElem = -1;
		int r = type.find("[");
		if (r != -1)
			nElem = std::atoi(type.substr(r+1, type.find("]")-r-1).c_str());
	}
};


struct writeInfo
{
	ADDRINT memOp, offset;
	variable var;
	fnlog f;
	int elPos;
	std::string accessType;
	bool stat;

	writeInfo() {;}
	writeInfo(std::string A, int E, fnlog F, ADDRINT M, ADDRINT O, bool S, variable V)
	{
		accessType = A; memOp = M; offset = O; var = V; f = F; elPos = E; stat = S;
	}
};

std::map <THREADID, std::map<ADDRINT, writeInfo>> writeTrace;



std::map<std::string, std::map <ADDRINT, variable>> funcLocalMap;  
												// funcname x offset -> varid

// std::map<std::pair<std::string, std::string>, ADDRINT> funcIDMap; // filename x funcname -> funcid
std::map <std::string, std::vector<std::string>> funcinfoMap;		// funcname -> vector<argtypes>


std::map <ADDRINT, variable> globalMap;								// global address -> var id
std::map <std::string, std::map<int, std::map<std::string, std::set<std::string>>>> funccallMap;		
														// fname x lineno x funcname -> vector<calls>

std::map <ADDRINT, variable>::iterator lookup (std::map <ADDRINT, variable>& mymap, ADDRINT addr, int& glob)
{
	std::map <ADDRINT, variable>::iterator it = mymap.lower_bound(addr);
	if (glob == 1 || it != mymap.end())
	{
		// outp << "\n\nADD: " << std::hex << it->first;
		if (glob == 1 && (it == mymap.end() || it->first != addr))
			it--;

		// outp << " " << std::hex << it->first << " ADD\n\n" << std::dec;

		// it = std::prev(it);
		ADDRINT diff = it->first - addr;
		if (glob == 1)
			diff *= -1;
		ssize_t size = it->second.size;
		int r = it->second.nElem;
		if (r != -1)
			size *= r;
		// outp << "GLOB: " << glob << " SIZE: " << size << " DIFF: " << diff << " ADDR: " << addr << " EST: " << it->first << "\n";
		// if (diff != 0)
		// 	outp << "\n\nADD: " << std::hex << it->first << " " << addr << std::dec << " << DIFF: " << diff << " Size: " << size << "\n\n";
		glob = r;
		if (size > diff)
		{
			if (r != -1)
				glob = diff/it->second.size;
			return it;
		}
	}
	return mymap.end();
}



/*			variables in stack - need to do later to handle references
std::map <ADDRINT, std::string> stackMap; // address -> variable node id
std::map <ADDRINT, std::pair<std::string, int offset>> stackMap;	// address -> routine x offset
// ^ maybe a better implementation as it decouples offset map from pintool
std::vector <std::pair <ADDRINT, std::pair <std::string, int>>> stackMap;
// ^ also a possible implementation: sorted list of RBP x RoutineName x InvocationNo
// ^ possibly the best way to do it
*/

// void print_state (const std::ios& stream, std::ostream& outf = std::cout) {
//   outf << " good()=" << stream.good();
//   outf << " eof()=" << stream.eof();
//   outf << " fail()=" << stream.fail();
//   outf << " bad()=" << stream.bad();
//   outf << "\n";
// }


// basic initialization
VOID init(std::string inp, std::string runid, std::string locf)
{
	// set up the type maps
	locks["mutex"] = 1;
	locks["semaphore"] = 2;
	locks["reader lock"] = 3;
	locks["writer lock"] = 4;
	unlocks[1] = "MUTEX";
	unlocks[2] = "SEMAPHONE";
	unlocks[3] = "READLOCK";
	unlocks[4] = "WRITELOCK";

	// initialize the lock
	PIN_InitLock(&globalLock);

	// open the output file
	std::string opfile = locf + runid + ".dump";
	outp.open(opfile.c_str());

	outp << "DYNAMICTRACE INP " << inp << " RUNID " << runid << " EXE " << locf << "\n";

	// offset file
	// FILENAME	FUNCTION	OFFSET	VARNAME	VARID	VARTYPE	VARSIZE	PARENTID

	{
		std::ifstream offFile((folder+foff).c_str());
		std::string filename, funcname, ignore;
		ADDRINT offset;
		variable var;

		// std::cout << "Opened " << folder+foff << "\n";

		if (offFile.good())
		{
			std::getline (offFile, ignore);
			// std::cout << ignore << ".\n";
			// std::cout << offFile.get() << ".\n";		
		}

		while (offFile.good())
		{
			offFile >> filename >> funcname >> hex >> offset >> dec >> var.name >> var.id;
			var.fname = funcname;
			offFile.get();
			std::getline (offFile, var.type, '\t');
			offFile >> var.size >> var.pid;
			var.patch();
			if (DEBUG)
				var.print(outp);

			funcLocalMap[funcname][offset] = var;
			// std::cout << funcname << "\n";
		}

		// for (auto i: funcLocalMap)
		// {
		// 	outp << i.first << "\n";
		// 	for (auto j : i.second)
		// 	{
		// 		outp << j.first << " ";
		// 		j.second.print(outp);
		// 	}
		// }
		// outp << "\n";

		offFile.close();

		// std::cout << "DAFUQ\n";
	}
	// offFile.open(goff.c_str());
	// while (offFile.good())
	// {
	// 	offFile >> offset >> var.name >> var.id;
	// 	offFile.get();
	// 	std::getline (offFile, var.type, '\t');
	// 	offFile >> var.size >> var.pid >> var.spattr;
	// 	if ((signed)(var.spattr.find("STATIC")) > 0)
	// 		offFile >> var.fname;
	// 	else
	// 		var.fname = "";
	// 	globalMap[offset] = var;
	// }
	
	// for (auto j: globalMap)
	// {
	// 	outp << std::hex << j.first << std::dec << ": ";
	// 	j.second.print(outp);
	// }
	// outp << "\n";
	
	// offFile.close();


	// argFile
	// FILENAME	FUNCNODEID	FUNCNAME NARGS	ARGTYPE* RETTYPE	
	{
		std::ifstream argFile((folder+fargs).c_str());
		// std::cout << folder << fargs << "\n\n";

		std::string filename, funcname, vartype, ignore, fnodeid;
		// bool add = true;
		int nargs;

		if (argFile.good())
		{
			std::getline (argFile, ignore);
			// std::cout << "\n" << ignore << ".\n";
			// argFile.get();		
		}


		while (argFile.good())
		{
			argFile >> filename >> fnodeid >> funcname >> nargs;
			argFile.get();
			// std::cout << funcname << " " << nargs << "\n";
			if (funcinfoMap.find(funcname) == funcinfoMap.end())
			{
				for (int i = 0; i < nargs; ++i)
				{
					std::getline (argFile, vartype, '\t');
					funcinfoMap[funcname].push_back(vartype);
				}
				std::getline (argFile, vartype, '\n');
				funcinfoMap[funcname].push_back(vartype);

				// std::cout << funcname << " " << nargs << "\n";
			}
			else
			{
				for (int i = 0; i < nargs; ++i)
					std::getline (argFile, vartype, '\t');
				std::getline (argFile, vartype, '\n');
			}
		}

	// while (offFile.good())
	// {
	// 	offFile >> fn >> nargs;
	// 	offFile.get();
	// 	for (int i = 0; i < nargs; ++i)
	// 	{
	// 		std::getline (offFile, vartype, '\t');
	// 		funcinfoMap[fn].push_back(vartype);
	// 	}
	// 	std::getline (offFile, vartype, '\n');
	// 	funcinfoMap[fn].push_back(vartype);
	// }


	// 	}

		// for (auto j: funcinfoMap)
		// {
		// 	outp << j.first << " Args: ";
		// 	auto& arglist = j.second;
		// 	int na = arglist.size()-1;
		// 	outp << na << " -> ";
		// 	for (int i = 0; i < na; ++i)
		// 		outp << arglist[i] << "... ";
		// 	outp << "Returns: " << arglist.back() << "\n";
		// }
		// outp << "\n";

		argFile.close();
	}

	// callFile
	// FILENAME	LINENUM	FUNCNAME	CALLNODEID	CALLEXPR
	{
		std::ifstream callFile((folder+fcalls).c_str());
		std::string filename, funcname, callsig, ignore, cnodeid;
		int lno;

		if (callFile.good())
		{
			std::getline (callFile, ignore);
			// callFile.get();		
		}
		
		while (callFile.good())
		{
			callFile >> filename >> lno >> funcname >> cnodeid;
			callFile.get();
			std::getline (callFile, callsig, '\n');
			funccallMap[filename][lno][funcname].insert(cnodeid + " " + callsig);
		}

		// for (auto j: funccallMap)
		// {
		// 	for (auto k: j.second)
		// 	{
		// 		for (auto l: k.second)
		// 		{
		// 			outp << "\n" << j.first << ": " << k.first << " ->" << l.first << " - ";
		// 			for (auto m: l.second)
		// 				outp << m << "\n";
		// 		}
		// 	}
		// }

		callFile.close();
	}
}


VOID ImageLoad(IMG img, VOID *v)
{
    std::string img_name = IMG_Name(img);
    ADDRINT img_loff = IMG_LoadOffset(img);

    // outp << "Loading " << img_name << ", Image loff = 0x" << hex << img_loff << dec << endl;

    std::string mainname = img_name.substr(img_name.rfind("/") + 1);

    std::ifstream addrFile((folder + mainname + faddr).c_str());
	std::string ignore;
	ADDRINT address;
	variable var;

	// while (offFile.good())
	// {
	// 	offFile >> fn >> offset >> var.id >> var.name;
	// 	var.fname = fn;
	// 	offFile.get();
	// 	std::getline (offFile, var.type, '\t');
	// 	offFile >> var.size >> var.pid;
	// 	funcLocalMap[fn][offset] = var;
	// }

	// // for (auto i: funcLocalMap)
	// // {
	// // 	outp << i.first << "\n";
	// // 	for (auto j : i.second)
	// // 	{
	// // 		outp << j.first << " ";
	// // 		j.second.print(outp);
	// // 	}
	// // }
	// // outp << "\n";

	// offFile.close();


	if (addrFile.good())
	{
		std::getline (addrFile, ignore);
		// callFile.get();
	}


	//ADDRESS	VARNAME	VARID	VARTYPE	VARSIZE	PARENTID	VARCLASS	[VARCONTAINER]

	while (addrFile.good())
	{
		addrFile >> hex >> address >> dec >> var.name >> var.id;
		addrFile.get();
		std::getline (addrFile, var.type, '\t');
		addrFile >> var.size >> var.pid >> var.spattr;
		if ((signed)(var.spattr.find("STATIC")) > 0)
			addrFile >> var.fname;
		else
			var.fname = "";
		var.patch();
		if (DEBUG)
			var.print(outp);
		if (var.name != "")
			globalMap[img_loff+address] = var;
	}
	
	// outp << img_name << "\n";
	// for (auto j: globalMap)
	// {
	// 	outp << std::hex << j.first << std::dec << ": ";
	// 	j.second.print(outp);
	// }
	// outp << "\n";
	
	addrFile.close();

}

// update rbp on change
VOID updateRBP (ADDRINT ina, THREADID tid, ADDRINT rbpval) 
{
	fnlog f(RTN_FindNameByAddress(ina), tid, rbpval);
	RBPstack[rbpval] = f; 
	// fnstack[f] = rbpval;
	invstack[tid].push_back(f);

	// outp << "INVOKED UPDATERBP\n\n";
	// printall();

	// outp << "FOR TID: " << tid << " RBP updated to " << rbpval << "\n";
	// outp << "Routine Stack:\n";
	// for (auto name: fnstack[tid])
	// 	outp << name << " ";
	// outp << "\nRBP Stack\n";
	// for (auto rbp: RBPstack[tid])
	// 	outp << std::hex << rbp << " ";
	// outp << "\n";
}

bool findPointee (ADDRINT memOp, THREADID tid, ADDRINT ina, writeInfo& u)
{
	u.memOp = memOp;
	u.elPos = 1;
	u.stat = false;
	bool found = false;
	std::map <ADDRINT, variable>::iterator it;

	// look in globals
	it = lookup(globalMap, memOp, u.elPos);
	if (it != globalMap.end())
	{
		u.var = it->second;
		u.accessType = u.var.spattr;
		found = true;
		u.stat = true;
	}
	else
	{
		u.elPos = 0;
		// look in current stack
		u.f = invstack[tid].back();
		u.offset = u.f.rbp - memOp;
		auto& curmap = funcLocalMap[u.f.fname];
		it = lookup(curmap, u.offset, u.elPos);
		if (it != curmap.end())
		{
			u.accessType = "LOCAL";	// local access
			u.var = it->second;
			found = true;
		}

		// look across other function invocations
		else
		{
			u.elPos = 0;
			auto itstack = RBPstack.upper_bound(memOp);

			if (itstack != RBPstack.end())
			{
				u.f = itstack->second;
				u.offset = itstack->first - memOp;	// get offset from current RBP
				// lookup in funcLocals
				auto& offMap = funcLocalMap[u.f.fname];
				it = lookup(offMap, u.offset, u.elPos);
				if (it != offMap.end())
				{
					u.accessType = "NONLOCALSTACK";	// nonlocal access
					u.var = it->second;
					found = true;
				}
				// else
				else if (DEBUG || VARSEARCH)
				 	outp << "VARSEARCH FAILED IN " << u.f.fname << "\n";
			}
		}
	}

	if (not found)
	{
		if (DEBUG || VARSEARCH)
		{
			outp << "VARIABLE NOT FOUND.... REAL ADDRESS: 0x" << std::hex << memOp << std::dec << ".\n";
			inslist[ina].shortPrint(outp);			
		}
	}

	return found;
}

VOID ptrWrite (THREADID tid, ADDRINT ina)
{
	writeInfo w = writeTrace[tid][ina];
	if (!w.var.isPtr)
		return;
	ADDRINT value;
	PIN_GetLock(&globalLock, 1);
	PIN_SafeCopy(&value, (ADDRINT *)w.memOp, sizeof(ADDRINT));
	PIN_ReleaseLock(&globalLock);
	outp << "POINTERWRITE";
	outp << " THREADID " << tid << " VARCLASS " << w.accessType;		// print thread id and access type
	if (value == 0)
		outp << " POINTEE NULL";
	else
	{
		outp << " WRITEVALUE 0x" << std::hex << value << std::dec;
		writeInfo v;
		bool found = findPointee(value, tid, ina, v);
		if (found)
		{
			outp << " POINTEEID " << v.var.id << " POINTEECLASS " << v.accessType
				<< " POINTEENAME " << v.var.name;
			if (v.elPos != -1)
				outp << " POINTEEINDEX " << v.elPos;
			if (v.accessType == "NONLOCALSTACK")
				outp << " POINTEEFUNC " << v.f.fname << " POINTEEFUNCTID " << v.f.tid 
					<< " POINTEEFUNCINVNO " << v.f.invNo;
		}
	}
	if (w.stat)
	{
		if ((signed)(w.accessType.find("STATIC")) > 0)
			outp << " VARCONTAINER " << w.var.fname;
		outp << " ADDRESS 0x" << std::hex << w.memOp << std::dec;
	}
	else 
	{
		if (w.accessType == "NONLOCALSTACK")
			outp << " VARFUNCNAME " << w.f.fname << " VARFUNCTID " << w.f.tid << " VARFUNCINVNO " << w.f.invNo;
			// function linkage name PIN_UndecorateSymbolName(fnstack[tid][idx], UNDECORATION_NAME_ONLY)
		outp << " OFFSET 0x" << std::hex << w.offset << std::dec;
	}
	outp << " VARNAME " << w.var.name << " VARID " << w.var.id;
	if (w.elPos != -1)
		outp << " POS " << w.elPos;
	outp << " FUNCNAME " << inslist[ina].rtnName;
	// synchronization info
	outp << " SYNCS ";
	if (syncs.find(tid) != syncs.end())
	{
		outp << syncs[tid].size() << " ";
		for (auto l: syncs[tid])
			outp << "ADDRESS 0x" << std::hex << l.first << std::dec << " TYPE " << unlocks[l.second] << " ";
	}
	else
		outp << "ASYNC ";
	outp << "id " << std::dec << ++timeStamp << " ";						// event timestamp
	outp << "INVNO " << invMap[inslist[ina].rtnName][tid] << "\n";	// function invocation count	
}

// memory access event handler
VOID dataman (THREADID tid, ADDRINT ina, ADDRINT memOp)
{
	inslist[ina].memOp = memOp;		// set target memory address - helps in debugging later
	
	writeInfo u;
	bool found = findPointee(memOp, tid, ina, u);

	if (found)
	{
		// inslist[ina].shortPrint(outp);
		
		// save what you have learnt and return
		writeTrace[tid][ina] = u;
		if (u.var.isPtr && inslist[ina].flag == 'w')
			return;

		if (inslist[ina].flag == 'r')
			outp << "READ";
		else if (inslist[ina].flag == 'w')
			outp << "WRITE";
		outp << " THREADID " << tid << " VARCLASS " << u.accessType;		// print thread id and access type
		if (u.stat)
		{
			if ((signed)(u.accessType.find("STATIC")) > 0)
				outp << " VARCONTAINER " << u.var.fname;
			outp << " ADDRESS 0x" << std::hex << memOp << std::dec;
		}
		else 
		{
			if (u.accessType == "NONLOCALSTACK")
				outp << " VARFUNCNAME " << u.f.fname << " VARFUNCTID " << u.f.tid
					 << " VARFUNCINVNO " << u.f.invNo;
				// function linkage name PIN_UndecorateSymbolName(fnstack[tid][idx], UNDECORATION_NAME_ONLY)
			outp << " OFFSET 0x" << std::hex << u.offset << std::dec;
		}
		outp << " VARNAME " << u.var.name << " VARID " << u.var.id;
		if (u.elPos != -1)
			outp << " POS " << u.elPos;
		outp << " FUNCNAME " << inslist[ina].rtnName;
		// synchronization info
		outp << " SYNCS ";
		if (syncs.find(tid) != syncs.end())
		{
			outp << syncs[tid].size() << " ";
			for (auto l: syncs[tid])
				outp << "ADDRESS 0x" << std::hex << l.first << std::dec << " TYPE " << unlocks[l.second] << " ";
		}
		else
			outp << "ASYNC ";

		outp << "id " << std::dec << ++timeStamp << " ";						// event timestamp
		outp << "INVNO " << invMap[inslist[ina].rtnName][tid] << "\n";	// function invocation count	
	}
}

// prints value of an arg, typecasting it to the given type
VOID printval (ADDRINT * arg, std::string type)
{
	if (type == "int")
		outp << *((int *)(arg));
	else if (type == "char")
		outp << "\'" << *((char *)(arg)) << "\'";
	else if (type == "float")
		outp << *((int *)(arg));
	else if (type == "double")
		outp << *((double *)(arg));
	else if (type == "char *")
		outp << "\"" << *((char **)(arg)) << "\"";
	else if (type == "void")
		outp << "void";
	else 
		outp << "UNKNOWN";
}

// funcation call event handler
VOID callP (THREADID tid, ADDRINT ina, int count, ...)
{
	// THREADID tid = va_arg(ap, THREADID);
	// ADDRINT ina = va_arg(ap, ADDRINT);

	// invMap[inslist[ina].target][tid]++;							// one more invocation of target
	outp << "CALL THREADID " << tid << " ";							// event type and thread id
	outp << "CALLERNAME " << inslist[ina].rtnName << " ";			// caller linkage name
	outp << "CALLEENAME " << inslist[ina].target << " ";			// callee linkage name
	outp << "id " << std::dec << ++timeStamp << " ";						// event timestamp
	std::string dyntarget = inslist[ina].target;
	dyntarget = dyntarget.substr(0, dyntarget.find("@plt"));		// removing @PLT's
	if (count > 0)
	{
		auto& argvec = funcinfoMap[dyntarget];							// argument types
		va_list ap;
		va_start (ap, count);
		for (int i = 0; i < count; ++i)									// printing arguments
		{
			ADDRINT * val = va_arg(ap, ADDRINT *);
			outp << "ARG" << i << " ";
			printval (val, argvec[i]);
			outp << " ";
		}
		va_end(ap);		
	}
	if (count == 0)
		outp << "ARGS NONE ";
	outp << "STATICCALL [\t";
	for (auto q: funccallMap[inslist[ina].fname][inslist[ina].line][dyntarget])
		outp << q << "\t";
	outp << "] ";
	outp << "INVNO " << invMap[inslist[ina].rtnName][tid] << "\n";	// function invocation count
}

VOID invP (THREADID tid, ADDRINT ina)
{
	std::string rtnName = RTN_FindNameByAddress(ina);
	invMap[rtnName][tid]++;
	
	// exit(0);
	// fnstack[tid].push_back(rtnName);
	// RBPstack[tid].push_back(0);

	// outp << "Someone invoked. Routine Stack:\n";
	// for (auto name: fnstack[tid])
	// 	outp << name << " ";
	// outp << "\n";
}


VOID retP (THREADID tid, ADDRINT ina, ADDRINT * retval)
{
	// outp << "INVOKED RETP\n\n";
	// outp << "PREREMOVAL\n\n";
	// printall();
	
	fnlog f = invstack[tid].back();
	outp << "RETURN THREADID " << f.tid << " ";							// event type and thread id
	outp << "FUNCNAME " << f.fname << " ";							// returning function
	outp << "id " << std::dec << ++timeStamp << " ";						// event timestamp
	if (funcinfoMap.find(f.fname) != funcinfoMap.end())
	{
		std::string rettype = funcinfoMap[f.fname].back();
		outp << "RETVAL ";
		printval(retval, rettype);
		outp << " ";
	}
	outp << "INVNO " << f.invNo << "\n";	// function invocation count

	// fnlog f(RTN_FindNameByAddress(ina), tid, ino);
	// ADDRINT rbpval = fnstack[f];
	// fnstack.erase(f);
	invstack[tid].pop_back();
	if (invstack[tid].empty())
		invstack.erase(tid);
	RBPstack.erase(f.rbp);

	// outp << "POSTREMOVAL\n\n";
	// printall();

	// outp << "Someone returned. Routine Stack:\n";
	// for (auto name: fnstack[tid])
	// 	outp << name << " ";
	// for (auto rbp: RBPstack[tid])
	// 	outp << std::hex << rbp << " ";
	// outp << "\n";
}

// filters and saves instructions to instrument
VOID Instruction(INS ins, VOID * v)
{
	ADDRINT ina = INS_Address(ins);
	int column, line;
	std::string fname;

	PIN_LockClient();
	PIN_GetSourceLocation(ina, &column, &line, &fname);			// get source information
	PIN_UnlockClient();

	if (fname.length() > 0 && fname.find("/usr") == -1)		// instrument only instructions whose source location is available
	{
		if (inslist.find(ina) == inslist.end())
			inslist[ina] = INSINFO(ins, fname, column, line);	// add to list
		if (DEBUG)
			inslist[ina].shortPrint(outp);

		// if it is a call event
		std::string target = inslist[ina].target;
		int nargs = 0;
		if (target != "")
		{
			if (funcinfoMap.find(target) != funcinfoMap.end())
				nargs = funcinfoMap[target].size() - 1;

			if (nargs == 0)
				INS_InsertCall(
				ins, IPOINT_BEFORE, (AFUNPTR)callP,
				IARG_THREAD_ID, IARG_ADDRINT, ina,
				IARG_UINT32, 0, IARG_END);
			else
			{
				IARGLIST mylist = IARGLIST_Alloc();
				for (int i = 0; i < nargs; ++i)
					IARGLIST_AddArguments(mylist, IARG_FUNCARG_CALLSITE_REFERENCE, i, IARG_END);
				INS_InsertCall(
				ins, IPOINT_BEFORE, (AFUNPTR)callP,
				IARG_THREAD_ID, IARG_ADDRINT, ina,
				IARG_UINT32, nargs, IARG_IARGLIST, mylist,
				IARG_END);
				IARGLIST_Free(mylist);
			}
		}

		// if it updates rbp
		int t = inslist[ina].rbploc;

		if (t != -1)
		{
			//inslist[ina].shortPrint(outp);
			INS_InsertCall(
			ins, IPOINT_AFTER, (AFUNPTR)updateRBP,
			IARG_ADDRINT, ina, IARG_THREAD_ID,
			IARG_REG_VALUE, INS_RegW(ins, t),
			IARG_END);
		}
			

		// if it is a memory access
		if (inslist[ina].flag != 'n')
		{
			INS_InsertCall(
			ins, IPOINT_BEFORE, (AFUNPTR)dataman,
			IARG_THREAD_ID, IARG_ADDRINT, ina,
			IARG_MEMORYOP_EA, 0,
			IARG_END);
			if (inslist[ina].flag == 'w')
				INS_InsertCall(
				ins, IPOINT_AFTER, (AFUNPTR)ptrWrite,
				IARG_THREAD_ID, IARG_ADDRINT, ina,
				IARG_END);
		}

		if (INS_IsRet(ins))
			INS_InsertCall(
			ins, IPOINT_BEFORE, (AFUNPTR)retP, 
			IARG_THREAD_ID, IARG_INST_PTR, 
			IARG_FUNCRET_EXITPOINT_REFERENCE,
			IARG_END);
		
		// else
		// 	INS_InsertCall(
		// 	ins, IPOINT_BEFORE, (AFUNPTR)dataman,
		// 	IARG_THREAD_ID, IARG_ADDRINT, ina,
		// 	IARG_ADDRINT, -1,
		// 	IARG_END);
	}
}

// synchronization lock acquisition event handler
VOID lock_func_bf (THREADID tid, ADDRINT addr, int type, ADDRINT rta)
{
	syncs[tid][addr] = type;													// thread id and lock variable address
	outp << "LOCK TID " << tid << " ADDRESS 0x" << std::hex << addr;					// event record
	outp << " TYPE " << unlocks[type] << " id " << std::dec << ++timeStamp << "\n";
}

/*		need to check out why this does not work
VOID lock_func_af (THREADID tid, ADDRINT addr, int type, ADDRINT rta)
{
	PIN_LockClient();
	RTN rtn = RTN_FindByAddress(rta);
	RTN_Open(rtn);
	INS ins = RTN_InsHead(rtn);
	RTN_Close(rtn);
	PIN_UnlockClient();
	INSINFO l(ins);
	outp << "MILA MILA!!!!! DOOSRA!!\n";
	l.print();
	outp << "\n\n";

	syncs[tid][addr] = type;
	outp << "setting syncs " << tid << " " << addr << "\n";
}*/

// synchronization lock release event handler
VOID unlock_func(THREADID tid, ADDRINT addr, ADDRINT rta)
{
	// if (syncs.find(tid) == syncs.end())
	// 	outp << "\n\nDAFUQ!!\n";
	// else
	// {
		outp << "UNLOCK TID " << tid << " ADDRESS 0x" << std::hex << addr;			// event record
		outp << " TYPE " << unlocks[syncs[tid][addr]] << " id " << std::dec << ++timeStamp << "\n";
		auto loc = syncs[tid].find(addr);				// unset the locks for thread
		syncs[tid].erase(loc);
		if (syncs[tid].size() == 0)						// remove thread from list if it holds no locks
			syncs.erase(syncs.find(tid));
	// }
}

// Looking for POSIX locking mechanisms
VOID Routine (RTN rtn, VOID * v)
{
	ADDRINT rta = RTN_Address(rtn);

	int column, line;
	std::string fname;

	PIN_LockClient();
	PIN_GetSourceLocation(rta, &column, &line, &fname);			// get source information
	PIN_UnlockClient();

	if (fname.length() > 0 && fname.find("/usr") == -1)		// instrument only instructions whose source location is available
	{
		RTN_Open(rtn);
		// string rtnName = RTN_Name(rtn);
		// outp << fname << "\n" << rtnName << "\n";
		
		// for (INS ins = RTN_InsHead(rtn); INS_Valid(ins); ins = INS_Next(ins))
		// {
		// 	ADDRINT ina = INS_Address(ins);
		// 	PIN_LockClient();
		// 	PIN_GetSourceLocation(ina, &column, &line, &fname);			// get source information
		// 	PIN_UnlockClient();
		// 	INSINFO(ins, fname, column, line).print(outp);
		// }

		RTN_InsertCall(rtn, IPOINT_BEFORE,
			(AFUNPTR)invP, IARG_THREAD_ID,
			IARG_ADDRINT, rta, IARG_END);

		// for (INS ins = RTN_InsHead(rtn); INS_Valid(ins); ins = INS_Next(ins))
		// 	if (INS_IsRet(ins))
		// 		INS_InsertCall(ins, IPOINT_BEFORE,
		// 		(AFUNPTR)retP, IARG_THREAD_ID,
		// 		IARG_INST_PTR, IARG_END);

		RTN_Close(rtn);
	}

	// if any of these locking functions is called
	std::string rname = RTN_Name(rtn), pat = "";
	if (rname == "pthread_mutex_lock@plt")
		pat = "mutex";
	else if (rname == "sem_wait")
		pat = "semaphore";
	else if (rname == "__pthread_rwlock_rdlock")
		pat = "reader lock";
	else if (rname == "__pthread_rwlock_wrlock")
		pat = "writer lock";

	// call the lock acquisition event handler
	if (pat != "")
	{
		RTN_Open(rtn);
		RTN_InsertCall(rtn, IPOINT_BEFORE,
			(AFUNPTR)lock_func_bf,
			IARG_THREAD_ID, IARG_FUNCARG_ENTRYPOINT_VALUE, 0,
			IARG_UINT64, locks[pat], IARG_INST_PTR,
			IARG_END);
		// RTN_InsertCall(rtn, IPOINT_AFTER,
		// 	(AFUNPTR)lock_func_af,
		// 	IARG_THREAD_ID, IARG_FUNCARG_ENTRYPOINT_VALUE, 0,
		// 	IARG_UINT64, locks[pat], IARG_INST_PTR,
		// 	IARG_END);
		RTN_Close(rtn);
	}

	// if any of the unlocking functions is called
	if (rname == "pthread_mutex_unlock@plt" || rname == "thread_rwlock_unlock" || rname == "sem_post")
	{
		// call the lock release event handler
	 	RTN_Open(rtn);
		RTN_InsertCall (rtn, IPOINT_BEFORE,
			(AFUNPTR) unlock_func,
			IARG_THREAD_ID, IARG_FUNCARG_ENTRYPOINT_VALUE, 0,
			IARG_INST_PTR, IARG_END);
		RTN_Close(rtn);
	}
}

/*		now decoupled from pintool
void initMaps (std::string locf)
{
	std::string opfile = locf + ".dump";
	outp.open(opfile.c_str());

	int ofst;
	std::string varfile = locf + "_combined.offset", func, id;
	std::ifstream vars(varfile.c_str());

	if (vars.is_open())
	{
		while (!vars.eof())
		{
			vars >> func >> ofst >> id;
			varmap[func][ofst] = id;
		}
		vars.close();
	}
	else
	{
		std::outp << "No such file " << varfile << "\n";
		// exit(1);
	}
}
*/

// close output file on exit
VOID Fini (INT32 code, VOID * v)
{
	outp.close();
}

int main(int argc, char * argv[])
{
	// Initialize pin & symbol manager
	PIN_Init(argc, argv);
	PIN_InitSymbols();

	if (DEBUG)
	{
		for (int i = 0; i < argc; ++i)
			std::cout << i << " " << argv[i] << "\n";
	}

	// get the input, runid, outdump
	std::string inp(argv[5]);
	inp = inp.substr(inp.find("=")+1);
	if (inp == "")
		inp = "[None]";
	std::string runid(argv[6]);
	runid = runid.substr(runid.find("=")+1);
	std::string locf(argv[7]);
	locf = locf.substr(locf.find("=")+1);
	locf = locf.substr(locf.find_last_of("/") + 1, locf.find_last_of(".") - locf.find_last_of("/") - 1);

	// basic variable initializations
	init(inp, runid, locf);
	IMG_AddInstrumentFunction(ImageLoad, 0);
	RTN_AddInstrumentFunction(Routine, 0);		// Routine level Instrumentation for locking and invocation events
	INS_AddInstrumentFunction(Instruction, 0);	// Instruction level Instrumentation for all other events
	PIN_AddFiniFunction(Fini, 0);				// Closing output file at the end
	
	// Start the program, never returns
	PIN_StartProgram();

	return 0;
}
