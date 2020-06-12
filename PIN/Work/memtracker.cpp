#include "memtracker.h"
#include <map>
#include <algorithm>
#include <fstream>
#include <iterator>
#include <set>
#include <cstdlib>

#define DEBUG false
#define VARSEARCH false

// major things left to do:
// 1. try making lock_func_af work using IPOINT_BEFORE on return
// 2. tracing reallocs
// 3. simplify the undecoration thing for funcinfomap

/* GLOBALS */

// static generated files that we read from
std::string folder = "statinfo/";
std::string foff = "final.offset";
std::string faddr = ".address";
std::string fargs = "final.funcargs";
std::string fcalls = "final.calls.tokens";

// information from static side
// global variables: global address -> var id
std::map <ADDRINT, variable> globalMap;
// local variables: funcname x offset -> variable
std::map<std::string, std::map <ADDRINT, variable>> funcLocalMap;
// functions: funcname -> <function clang id, vector<argtypes>, return type>
std::map <std::string, std::vector<std::string>> funcinfoMap;
// calls: fname x lineno x funcname -> set<calls>
std::map <std::string, std::map<int, std::map<std::string, std::set<std::string>>>> funccallMap;

// PIN Global Lock
PIN_LOCK globalLock;

// event globals
std::string runid;				// runid passed from examine. prepended to timestamps to make unique
long long int timeStamp = 0;	// global event timestep
std::ofstream outp;				// file to write to

// all instrumented instructions
std::map <ADDRINT, INSINFO> inslist;

/* tracing runtime stack */
// to trace function invocations: function name x thread id -> no. of invocations
std::map <std::string, std::map<THREADID, int>> invMap;
// to trace function returns: threadid -> current function invocation stack
// also needed to distinguish stack memory accesses within current function (local)
// vs stack memory accesses from other functions (non-local) eg: local variables passed via pointers
// see findVar for more details on this
std::map <THREADID, std::vector <fnlog>> invstack;
// to trace locks: thread -> <lock address, lock type>
std::map <THREADID, std::map<ADDRINT, ADDRINT>> syncs;
std::string unlocks[] = {"MUTEX", "SEMAPHORE", "READLOCK", "WRITELOCK"};// lock names

/* tracing variables in runtime */
// to trace local memory acceses: base pointer -> function info
std::map <ADDRINT, fnlog> RBPstack;
// to return results from variable search: threadid x ins address -> accessInfo
// used for faster tracing of pointer writes
std::map <THREADID, std::map<ADDRINT, accessInfo>> writeTrace;

/* tracing heap memory */
long long int mallocid = 0;				// id for each malloc
std::map <THREADID, ADDRINT> lastReq;	// last heap request size from this thread
std::map <ADDRINT, variable> heapMap;	// heap map: memory location -> allocated size


/* DEBUG FUNCTIONS - JUST PRINT STUFF */

// prints globalMap
void printGlobal(std::ostream& outf = std::cerr)
{
	for (auto j: globalMap)
	{
		outf << hex << j.first << dec << ": ";
		j.second.print(outf);
	}
	outf << "\n";
}

// prints funcLocalMap
void printfLocal(std::ostream& outf = std::cerr)
{
	for (auto i: funcLocalMap)
	{
		outf << i.first << "\n";
		for (auto j : i.second)
		{
			outf << j.first << " ";
			j.second.print(outf);
		}
	}
	outf << "\n";
}

// prints funcinfoMap
void printfInfo(std::ostream& outf = std::cerr)
{
	for (auto j: funcinfoMap)
	{
		auto& arglist = j.second;
		int na = arglist.size()-1;
		outf << j.first << " ID: " << arglist[0] << " Args: ";
		outf << na << " -> ";
		for (int i = 1; i < na; ++i)
			outf << arglist[i] << "... ";
		outf << "Returns: " << arglist.back() << "\n";
	}
	outf << "\n";
}

// prints funccallMap
void printfCall(std::ostream& outf = std::cerr)
{
	for (auto j: funccallMap)
	{
		for (auto k: j.second)
		{
			for (auto l: k.second)
			{
				outf << "\n" << j.first << ": " << k.first << " ->" << l.first << " - ";
				for (auto m: l.second)
					outf << m << "\n";
			}
		}
	}
}

// prints the RBPstack
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

// prints the invstack
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

// prints RBP & inv stacks
void printall()
{
	printRBP(outp);
	printinv(outp);
}


/* HELPER FUNCTIONS - For tracing variables at runtime */

// given a memory address addr
// looks for the corresponding variable in the address map mymap
// glob denotes whether the map is global or on stack
// returns the iterator to element if found, mymap.end() otherwise
// glob is required since global memory grows upward, while stack grown downward
std::map <ADDRINT, variable>::iterator lookup (std::map <ADDRINT, variable>& mymap, ADDRINT addr, int& glob)
{
	// find the lowest address, that is greater than or equal to addr
	std::map <ADDRINT, variable>::iterator it = mymap.lower_bound(addr);

	/* IMP NOTE ON HOW GLOBAL/LOCAL MEMORY AFFECTS SEARCH
	* If global memory:
	1. Say, a variable X is at address 24. let it's size be 12 bytes. So, it occupies space from 24-36.
	Now, if someone accesses address 28, then, we should return X.
	2. Also, note that if some Y is above X ie at address 36, lower_bound will hit the address for Y,
	when you search for 28. However, it will hit X directly if you search for 24.
	3. Also, note that if X is the variable with highest address (nobody above X), then lower_bound
	on searching for 28 would give mymap.end() as nobody above X. So, keep this in mind.

	* If local memory:
	1. Say, a variable X is at address 24. let it's size be 12 bytes. So, it occupies space from 24-12.
	Now, if someone accesses address 18, then, we should return X.
	2. Also, note that lower_bound will hit X only whether one searches for 18 or 24.
	* Note the convention that we mention base address first (24-36 or 24-12), no matter where memory grows
	*/

	// if map is not empty
	// and either the map is global, so lower_bound can hit mymap.end()
	// or in the local case, lower_bound is not mymap.end()
	if (!mymap.empty() && (glob == 1 || it != mymap.end()))
	{
		if (DEBUG)
		{
			std::cout << "\n\nSEARCHING FOR: 0x" << hex << addr << dec << " INITADD: ";
			if (it != mymap.end()) 
				std::cout << "0x" << hex << it->first << dec;
			else
				std::cout << "MAPEND";
		}

		// in case of global map, if the address of lower_bound has crossed addr
		// or, we are at the map end, then we have overshot the variable we are looking for
		// so, bring iterator one step down
		if (glob == 1 && (it == mymap.end() || it->first != addr))
			it--;

		if (DEBUG)
			std::cout << " POSTUPDATE: 0x" << hex << it->first << dec << "\n";


		// so `it` now holds the pointer to our guess for addr
		// note that in case of local, lower_bound must definitely hit the variable we are looking for
		// or we shall reach mymap.end()

		// we get the difference from your 'guess' for the variable, and addr
		ADDRINT diff = it->first - addr;
		// if global map, the difference would be addr - <guess variable address>
		if (glob == 1)
			diff *= -1;

		// this difference should be within the `size` of our variable.
		// so, if our guess variable was at 24-36, and the access was at 40
		// the difference would be 40-24 = 16. but variable size is only 12.
		// so this is a miss.

		// get the size of variable base type
		ssize_t size = it->second.size;

		// if variable is array, then actual size is nElem * size
		int r = it->second.nElem;
		if (r != -1)
			size *= r;

		if (DEBUG)
			std::cout << "GLOB: " << glob << " SIZE: " << size << " DIFF: " << diff << "\n\n";

		// if the variable is an array, we will reuse glob
		// to return which position in the array the access was made at
		glob = r; // -1 if no elements

		// check if diff < size
		if (size > diff)
		{
			// if variable is array, get the array index as difference/(size of base type)
			if (r != -1)
				glob = diff/it->second.size;
			// return the iterator
			return it;
		}
	}
	// otherwise return mymap.end()
	return mymap.end();
}

// looks for the access to memOp by instruction ina in thread tid, across all maps
// if found returns true, & u contains the variable information
// else returns false
bool findVar (ADDRINT memOp, THREADID tid, ADDRINT ina, accessInfo& u)
{
	// initialize u
	u.memOp = memOp;
	u.elPos = 1;	// done to tell lookup that search is in global memory
	u.stat = false;
	bool found = false;

	// look in globalMap
	auto it = lookup(globalMap, memOp, u.elPos);
	if (it != globalMap.end())
	{	// if found, fill in the remaining info
		u.var = it->second;
		u.accessType = u.var.spattr;
		u.stat = true;
		found = true;
	}
	else
	{	// else look in the stack memory
		u.elPos = 0;	// done to tell lookup that search is in stack memory
		// first, look in current function's stack
		u.f = invstack[tid].back();	// fnlog for current function
		u.offset = u.f.rbp - memOp;	// offset from rbp
		auto& curmap = funcLocalMap[u.f.fname];	// get the map for f
		it = lookup(curmap, u.offset, u.elPos);	// find this offset within f's stack
		if (it != curmap.end())
		{	// if found, fill in the remaining info
			u.accessType = "LOCAL";	// local access
			u.var = it->second;
			found = true;
		}
		// look across other function invocations
		else
		{
			u.elPos = 0;	// done to tell lookup that search is in stack memory
			
			// find which function stack bounds this access
			auto itstack = RBPstack.upper_bound(memOp);
			// check if the access isn't beyond all stack memory
			if (itstack != RBPstack.end())
			{	// get info for whichever function it falls into
				u.f = itstack->second;
				u.offset = itstack->first - memOp;	// get offset from that RBP
				auto& offMap = funcLocalMap[u.f.fname];	// get the map for that function
				it = lookup(offMap, u.offset, u.elPos);	// find this offset within that function's stack
				if (it != offMap.end())
				{	// if found, fill in the remaining info
					u.accessType = "NONLOCALSTACK";	// nonlocal access on stack
					u.var = it->second;
					found = true;
				}
				else
				{	// else look in heap map
					// std::cerr << "LOOKING IN HEAP MAP\n";
					u.elPos = 1;	// done to tell lookup that search is in heap memory
					it = lookup(heapMap, memOp, u.elPos);
					// std::cerr << "THIS??\n";
					if (it != heapMap.end())
					{	// if found, fill in the remaining info
						u.var = it->second;
						u.accessType = u.var.spattr;
						u.stat = true;
						found = true;
					}
					else if (DEBUG || VARSEARCH)
				 		std::cout << "\nVARSEARCH FAILED IN " << u.f.fname << " OFFSET " << 
				 			hex << u.offset << dec;
				}
			}
		}
	}

	if (not found)
	{
		if (DEBUG || VARSEARCH)
		{
			std::cout << "\nVARIABLE NOT FOUND.... REAL ADDRESS: 0x" << hex << memOp << dec << "\n";
			inslist[ina].shortPrint(std::cout);
		}
	}

	return found;
}

// prints value at any address, typecasting it to the given type
// used for tracing call arguments & return values for functions
// currently we only support basic standard types
VOID printval (ADDRINT * arg, std::string type)
{
	if (type == "int")
		outp << *((int *)(arg));
	else if (type == "char")
		outp << "CH:" << int(*((char *)(arg)));
	else if (type == "float")
		outp << *((int *)(arg));
	else if (type == "double")
		outp << *((double *)(arg));
	// strings are causing segfault when people misuse pointers
	// or send unintialized pointers to functions
	// else if (type == "char *")
	// 	outp << "\"" << *((char **)(arg)) << "\"";
	else if (type == "void")
		outp << "void";
	else 
		outp << "UNKNOWN";
}


/* FUNCTION INVOCATION AND RETURN ANALYSIS CALLBACKS */

// function call event handler
// count: number of arguments of function called
// ...: variable sized list of argument values
VOID callP (THREADID tid, ADDRINT ina, int count, ...)
{
	if (DEBUG)
		std::cout << "IN CALLP\n";

	std::string rtnName = inslist[ina].rtnName;
	std::string dyntarget = inslist[ina].target;
	// removing "@plt" from linkage name for functions linked via plt
	// dyntarget = dyntarget.substr(0, dyntarget.find("@plt"));

	// record call event
	outp << "CALL THREADID " << tid << " ";
	// caller linkage name and clang node id
	outp << " CALLERNAME " << rtnName;
	if (funcinfoMap.find(undec(rtnName)) != funcinfoMap.end())
		outp << " CALLERNODEID " << funcinfoMap[undec(rtnName)][0];
	// callee linkage name and clang node id
	outp << " CALLEENAME " << dyntarget;
	if (funcinfoMap.find(undec(dyntarget)) != funcinfoMap.end())
		outp << " CALLEENODEID " << funcinfoMap[undec(dyntarget)][0];
	// print the caller's invocation number within this thread
	outp << " INVNO " << invMap[rtnName][tid] << " ";

	// printing call site arguments
	if (count == 0)
		outp << "ARGS NONE "; // print no args if count is 0
	else if (count > 0)
	{
		auto& argvec = funcinfoMap[undec(dyntarget)];	// argument types
		va_list ap;
		va_start (ap, count);
		// printing arguments
		for (int i = 0; i < count; ++i)
		{
			ADDRINT * val = va_arg(ap, ADDRINT *);
			outp << "ARG" << i << " ";
			printval (val, argvec[i]);
			outp << " ";
		}
		va_end(ap);
	}

	// printing possible call node ids
	outp << "STATICCALL [\t";
	// print the call expressions at this location, for the current target function
	for (auto q: funccallMap[inslist[ina].fname][inslist[ina].line][dyntarget])
		outp << q << "\t";
	outp << "] ";

	outp << "INSLOC " << inslist[ina].fname << ":" << inslist[ina].line << " "; //file location
	outp << "TS " << dec << runid << "_" << ++timeStamp << "\n";// event timestamp
}


// updates invocation count of the function called
VOID invP (THREADID tid, ADDRINT ina)
{
	std::string rtnName = RTN_FindNameByAddress(ina);
	invMap[rtnName][tid]++;

	// if (DEBUG)
	// 	printall();
}


// update RBPstack and invstack, when a new stack is set up
// captured by the updation of rbp
VOID updateRBP (ADDRINT ina, THREADID tid, ADDRINT rbpval) 
{
	if (DEBUG)
		std::cout << "IN UPDATERBP\n";

	std::string rtn = RTN_FindNameByAddress(ina);
	fnlog f(rtn, tid, invMap[rtn][tid], rbpval);	// create the fnlog entry

	RBPstack[rbpval] = f; // update RBPstack for new value of RBP
	invstack[tid].push_back(f);	// add this function to the current invocation stack for tid

	// if (DEBUG)
	// 	printall();
}


// records a return event
// updates RBPstack and invstack accordingly
// return value is passed as retval
VOID retP (THREADID tid, ADDRINT ina, ADDRINT * retval)
{
	// outp << "INVOKED RETP\n\n";
	// outp << "PREREMOVAL\n\n";
	// printall();

	if (DEBUG)
		std::cout << "IN RETP\n";

	// get the function
	fnlog f = invstack[tid].back();
	outp << "RETURN THREADID " << f.tid;
	// returning function and its clang node id
	outp << " FUNCNAME " << f.fname;
	if (funcinfoMap.find(undec(f.fname)) != funcinfoMap.end())
		outp << " FUNCNODEID " << funcinfoMap[undec(f.fname)][0];
	// print the function's invocation number within this thread
	outp << " INVNO " << f.invNo << " ";

	// print return value if possible
	if (funcinfoMap.find(undec(f.fname)) != funcinfoMap.end())
	{
		// last element of funcinfoMap entry holds the return type
		std::string rettype = funcinfoMap[undec(f.fname)].back();
		outp << "RETVAL ";
		printval(retval, rettype);
		outp << " ";
	}

	outp << "INSLOC " << inslist[ina].fname << ":" << inslist[ina].line << " "; //file location
	outp << "TS " << dec << runid << "_" << ++timeStamp << "\n";// event timestamp

	// remove function from invstack of this thread
	invstack[tid].pop_back();
	// if there are no more functions in thread stack, it means the thread has completed its life
	if (invstack[tid].empty())
		invstack.erase(tid);
	// remove the function entry from RBPstack
	RBPstack.erase(f.rbp);

	// outp << "POSTREMOVAL\n\n";
	// printall();
}


/* LOCK EVENT ANALYSIS CALLBACKS */

// synchronization lock acquisition event handler
VOID lock_func_bf (THREADID tid, ADDRINT addr, ADDRINT type)
{
	// add the lock information to syncs for thread id, lock variable address & lock type
	syncs[tid][addr] = type;
	// record the lock event, with the lock type
	outp << "LOCK TID " << tid << " ADDRESS 0x" << hex << addr << " TYPE " <<
		unlocks[type] << " TS " << dec << runid << "_" << ++timeStamp << "\n";
}


/*		can't figure out why this does not work
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
	// record the unlock event
	outp << "UNLOCK TID " << tid << " ADDRESS 0x" << hex << addr << " TYPE " << 
		unlocks[syncs[tid][addr]]  << " TS " << dec << runid << "_" << ++timeStamp << "\n";

	auto loc = syncs[tid].find(addr);
	// remove this lock for the thread
	syncs[tid].erase(loc);
	// remove thread from syncs if it holds no locks
	if (syncs[tid].size() == 0)
		syncs.erase(syncs.find(tid));
}


/* MEMORY ACCESS EVENT ANALYSIS CALLBACKS */

// prints info about any variable accessed
// u is the accessInfo about the variable accessed
// memType denotes whether variable is normal VAR or POINTER or POINTEE
void printVarAccess(std::string memType, const accessInfo& u)
{
	// print variable name and id
	outp << memType << "NAME " << u.var.name;
	// don't have clang node id for heap variables
	if (u.var.spattr != "HEAP") 
		outp << " " << memType << "ID " << u.var.id;
	// print position if access is within an array
	if (u.elPos != -1)
		outp << " POS " << u.elPos;
	// print variable access type GLOBAL, LOCAL, FUNCSTATIC etc.
	outp << " " << memType << "CLASS " << u.accessType;

	// if it is static storage variable
	if (u.stat)
	{
		// print the address
		outp << " " << memType << "ADDRESS 0x" << hex << u.memOp << dec;
		// if FUNCSTATIC etc., then print the name of containing class/func etc.
		if ((signed)(u.accessType.find("STATIC")) > 0)
		{
			outp << " " << memType << "CONTAINERNAME " << u.var.fname;
			outp << " " << memType << "CONTAINERNODEID " << u.var.pid;
		}
	}
	// otherwise, it resides on the stack
	else 
	{
		// print the offset from its containing function's base pointer
		outp << " " << memType << "OFFSET 0x" << hex << u.offset << dec;

		// if it is not within the current function it is a non-local stack variable.
		// will have to print the information of containing function also
		if (u.accessType == "NONLOCALSTACK")
		{
			outp << " " << memType << "FUNCNAME " << u.f.fname;
			if (funcinfoMap.find(undec(u.f.fname)) != funcinfoMap.end())
				outp << " " << memType << "FUNCNODEID " << funcinfoMap[undec(u.f.fname)][0];
			outp << " " << memType << "FUNCTID " << u.f.tid
				 << " " << memType << "FUNCINVNO " << u.f.invNo;
			// function linkage name PIN_UndecorateSymbolName(fnstack[tid][idx], UNDECORATION_NAME_ONLY)
		}	
	}
}

// prints info for any access event
// eventType is READ/WRITE/POINTERWRITE
// memType denotes whether variable is normal VAR or POINTER or POINTEE
// u is the accessInfo about the variable accessed
// tid is THREADID, ina is instruction address for the instruction performing the access
// end is the terminating character for the event string
void printAccessEvent(std::string eventType, std::string memType, 
								const accessInfo& u, THREADID tid, ADDRINT ina, char end = '\n')
{
	std::string rtnName = inslist[ina].rtnName;
	outp << eventType << " THREADID " << tid;
	outp << " FUNCNAME " << rtnName;
	if (funcinfoMap.find(undec(rtnName)) != funcinfoMap.end())
		outp << " FUNCNODEID " << funcinfoMap[undec(rtnName)][0];
	outp << " INVNO " << invMap[rtnName][tid] << " ";	// function invocation count

	// print synchronization info during access
	outp << "SYNCS ";
	if (syncs.find(tid) != syncs.end())
	{
		// print number of locks
		outp << syncs[tid].size() << " ";
		// print each lock address and type
		for (auto l: syncs[tid])
			outp << "ADDRESS 0x" << hex << l.first << dec << " TYPE " << unlocks[l.second] << " ";
	}
	else // otherwise it is ASYNC access
		outp << "ASYNC ";

	printVarAccess(memType, u);

	outp << " INSLOC " << inslist[ina].fname << ":" << inslist[ina].line << " "; //file location
	outp << "TS " << dec << runid << "_" << ++timeStamp << end;	// event timestamp
}

// memory access event handler
// memOps are the addresses accessed by the instruction at address ina, within thread tid
// in general, read1 will come in memOp1
// for instructions with two reads, memOp2 would have the read2 address
// and writes would come in memOp3
VOID dataman (THREADID tid, ADDRINT ina, ADDRINT memOp1, ADDRINT memOp2, ADDRINT memOp3)
{
	if (DEBUG)
	{
		std::cout << "IN DATAMAN\n";
		inslist[ina].shortPrint(std::cout);
	}

	// setting target memory address - helps in debugging later
	inslist[ina].memR1 = memOp1;
	inslist[ina].memR2 = memOp2;
	inslist[ina].memW = memOp3;

	accessInfo u;
	bool found;

	if (memOp1 != -1)
	{
		found = findVar(memOp1, tid, ina, u);
		if (found)
			printAccessEvent("READ", "VAR", u, tid, ina);
	}
	if (memOp2 != -1)
	{
		found = findVar(memOp2, tid, ina, u);
		if (found)
			printAccessEvent("READ", "VAR", u, tid, ina);
	}
	if (memOp3 != -1)
	{
		found = findVar(memOp3, tid, ina, u);
		if (found)
		{
			// if it is a pointer write, then we save what we learnt and return.
			// ptrWrite called at IPOINT_AFTER is responsible to print this event.
			if (u.var.isPtr)
			{
				writeTrace[tid][ina] = u;
				return;
			}
			// otherwise, emit this event as well
			printAccessEvent("WRITE", "VAR", u, tid, ina);
		}
	}
}

// pointer write event handler
// tid is THREADID, ina is instruction address for the instruction performing the access
VOID ptrWrite (THREADID tid, ADDRINT ina)
{
	// the dataman call at IPOINT_BEFORE would have saved this for us
	auto tracetid = writeTrace.find(tid);
	// check for the tid
	if (tracetid != writeTrace.end())
	{
		auto& tidentry = tracetid->second;
		auto traceina = tidentry.find(ina);
		// check for the ina
		if (traceina != tidentry.end())
		{	
			if (DEBUG)
			{
				std::cout << "IN PTRWRITE\n";
				inslist[ina].shortPrint(std::cout);
			}

			// if present, print pointer info
			accessInfo& w = traceina->second;
			printAccessEvent("POINTERWRITE", "POINTER", w, tid, ina, ' ');
			
			// copy the value written into the pointer ie address of the pointee
			ADDRINT value;
			PIN_GetLock(&globalLock, 1);
			PIN_SafeCopy(&value, (ADDRINT *)w.memOp, sizeof(ADDRINT));
			PIN_ReleaseLock(&globalLock);

			// if pointee is NULL print so
			if (value == 0)
				outp << "POINTEE NULL";
			else
			{	// otherwise look for the pointee
				accessInfo v;
				bool found = findVar(value, tid, ina, v);
				// if found, print pointee info
				if (found)
					printVarAccess("POINTEE", v);
			}
			outp << "\n";
		}
	}
}

/* HEAP MEMORY ANALYSIS CALLBACKS */

// records last request from thread tid
// the request size is arg1 * arg2 (to accommodate malloc and calloc)
VOID addHeapRequest(THREADID tid, ADDRINT arg1, ADDRINT arg2)
{
	lastReq[tid] = arg1 * arg2;
}

// keeps track over where the last request was granted
VOID addHeapMap (THREADID tid, ADDRINT memOp)
{
	if (DEBUG)
		std::cerr << "CALLED MALLOC 0x" << hex << memOp << dec << "\n";
	// create a fictitious variable for this malloc
	variable v;
	v.name = "MALLOC_" + to_string(++mallocid);	// name according to malloc id
	v.id = mallocid;
	v.size = lastReq[tid];	// give it the size as required
	v.spattr = "HEAP";		// it resides on heap
	// add the entry at memOp
	heapMap[memOp] = v;
	// print the event details
	outp << "MALLOC TID " << tid << " BYTES " << lastReq[tid] << " MEMORY 0x" << hex << memOp << dec
		 << " TS " << runid << "_" << ++timeStamp << "\n";
}

// purges the heapMap entry on free
VOID remHeapMap (THREADID tid, ADDRINT memOp)
{
	if (DEBUG)
		std::cerr << "CALLED FREE 0x" << hex << memOp << dec << "\n";
	// find the location
	if (heapMap.find(memOp) != heapMap.end())
	{
		// print the event details
		outp << "FREE TID " << tid << " BYTES " << heapMap[memOp].size << " MEMORY 0x" << hex << memOp << dec
			 << " TS " << runid << "_" << ++timeStamp << "\n";
		// erase heap entry
		heapMap.erase(memOp);
	}
}


/* PIN INIT */

// basic initialization from statinfo
// fills in funcLocalMap, funcinfoMap & funccallMap
// note that globalMap is filled during ImageLoad as it depends on image load offset
VOID init(std::string inp, std::string runid, std::string locf)
{
	// initialize the lock
	PIN_InitLock(&globalLock);

	// open the output file
	std::string opfile = locf + "_" + runid + ".dump";
	outp.open(opfile.c_str());

	// Emit the runid, exe info
	outp << "DYNAMICTRACE INP " << inp << " RUNID " << runid << " EXE " << locf << "\n";

	// parse the offset file to fill funcLocalMap
	// HEADER: FILENAME FUNCTION OFFSET VARNAME VARID VARTYPE VARSIZE PARENTID
	{
		std::string filename, funcname, ignore;
		ADDRINT offset;
		variable var;
		std::map<std::string, std::string> fnfreeze;

		// open the file
		std::ifstream offFile((folder+foff).c_str());

		// ignore the header
		if (offFile.good())
			std::getline (offFile, ignore);

		// start reading
		while (offFile.good())
		{
			// get FILENAME FUNCTION OFFSET VARNAME VARID
			offFile >> filename >> funcname >> hex >> offset >> dec >> var.name >> var.id;
			// set variable's function name
			var.fname = funcname;
			// VARTYPE may contain spaces like `struct * ABC [2]`. So get until \t
			offFile.get();
			std::getline (offFile, var.type, '\t');
			// get VARSIZE & PARENTID
			offFile >> var.size >> var.pid;
			// update the nElem & isPtr from type info
			var.patch();

			funcname = undec(funcname);
			// add this information to funcLocalMap, if it wasn't present before
			if (fnfreeze.count(funcname) == 0)
				fnfreeze[funcname] = filename;
			if (filename == fnfreeze[funcname])
				funcLocalMap[funcname][offset] = var;
		}

		// close the file
		offFile.close();

		if (DEBUG)
			printfLocal();
	}

	// parse the arg file to fill funcinfoMap
	// HEADER: FILENAME FUNCNODEID FUNCNAME NARGS ARGTYPE* RETTYPE
	{
		std::string filename, ftempname, funcname, vartype, ignore, fnodeid;
		int nargs;

		// open the file
		std::ifstream argFile((folder+fargs).c_str());

		// ignore the header
		if (argFile.good())
			std::getline (argFile, ignore);

		// start reading
		while (argFile.good())
		{
			// get FILENAME FUNCNODEID FUNCNAME NARGS
			argFile >> filename >> fnodeid >> ftempname >> nargs;
			argFile.get();

			// funcinfoMap is based on demangled names
			// this is done because sometimes functions (like constructors) can have multiple
			// mangled names. eg: _ZN1AC1Ev, _ZN1AC2Ev, _ZN1AC4Ev are all equivalent. in such cases,
			// the PIN name might not match the name we get from static.
			funcname = undec(ftempname);

			// if this is the first time you're seeing this function, add info to funcinfoMap
			// functions may be seen multiple times if they are declared in multiple files
			// but only the first occurence is true, because of how the linker works
			if (funcinfoMap.find(funcname) == funcinfoMap.end())
			{
				// add the clang node id
				funcinfoMap[funcname].push_back(fnodeid);
				// add all arguments
				for (int i = 0; i < nargs; ++i)
				{
					// ARGTYPE may contain spaces like `struct * ABC [2]`. So get until \t
					std::getline (argFile, vartype, '\t');
					funcinfoMap[funcname].push_back(vartype);
				}
				// add return type
				std::getline (argFile, vartype, '\n');
				funcinfoMap[funcname].push_back(vartype);
			}
			// else if you've seen before ignore
			else
			{
				for (int i = 0; i < nargs; ++i)
					std::getline (argFile, ignore, '\t');
				std::getline (argFile, ignore, '\n');
			}
		}

		// close the file
		argFile.close();

		if (DEBUG)
			printfInfo();
	}

	// parse the call file to fill funccallMap
	// HEADER: FILENAME LOCATION FUNCNAME CALLNODEID FILENAME LOCATION FUNCNAME CALLNODEID
	{
		std::string filename, funcname, callsig, ignore, cnodeid;
		int lno;

		// open the file
		std::ifstream callFile((folder+fcalls).c_str());

		// ignore the header
		if (callFile.good())
			std::getline (callFile, ignore);

		// start reading
		while (callFile.good())
		{
			// get FILENAME LOCATION FUNCNAME CALLNODEID
			// clang gives location as 12:40::13:27 (start line, column, end line, column)
			// we only need start line, so we get lno, and ignore the rest
			callFile >> filename >> lno >> ignore >> funcname >> cnodeid;
			callFile.get();
			// CALLEXPR may contain spaces etc. so get until \n
			std::getline (callFile, callsig, '\n');
			// add information to funccallMap
			funccallMap[filename][lno][funcname].insert(cnodeid + " " + callsig);
		}

		// close the file
		callFile.close();

		if (DEBUG)
			printfCall();
	}
}


/* IMAGE LEVEL INSTRUMENTATION */

// populates the global variable map according to load offsets of images containing them
VOID ImageLoad(IMG img, VOID *v)
{
	std::string ignore;
	ADDRINT address;
	variable var;

	// get image name and load offset
	std::string img_name = IMG_Name(img);
	ADDRINT img_loff = IMG_LoadOffset(img);

	if (DEBUG)
		std::cerr << "Loading " << img_name << ", Image loff = 0x" << hex << img_loff << dec << endl;

	// find the main image name from the whole path
	std::string mainname = img_name.substr(img_name.rfind("/") + 1);
	// open corresponding address file
	std::ifstream addrFile((folder + mainname + faddr).c_str());

	// ignore header
	if (addrFile.good())
		std::getline (addrFile, ignore);

	// parse .address file to fill globalMap
	// HEADER: ADDRESS VARNAME VARID VARTYPE VARSIZE PARENTID VARCLASS [VARCONTAINER]
	while (addrFile.good())
	{
		// get ADDRESS VARNAME VARID
		addrFile >> hex >> address >> dec >> var.name >> var.id;
		addrFile.get();
		// VARTYPE may contain spaces like `struct * ABC [2]`. So get until \t
		std::getline (addrFile, var.type, '\t');
		// get VARSIZE PARENTID VARCLASS
		addrFile >> var.size >> var.pid >> var.spattr;
		// if FUNCSTATIC etc., get the name of containing class/struct/function
		if ((signed)(var.spattr.find("STATIC")) > 0)
			addrFile >> var.fname;
		else
			var.fname = "";
		// update the nElem & isPtr from type info
		var.patch();

		// add information to global map
		// actual address if image load offset + address from binary
		if (var.name != "")
			globalMap[img_loff+address] = var;
	}

	// close the file
	addrFile.close();

	if (DEBUG)
		printGlobal();

	// Instrumenting heap memory routines
	{	// look for malloc
		RTN mallocRtn = RTN_FindByName(img, "malloc");
		if (RTN_Valid(mallocRtn))
		{
			RTN_Open(mallocRtn);
			// Instrument to print the input argument value (size requested)
			// and the return value (memory location allocated)
			RTN_InsertCall(mallocRtn, IPOINT_BEFORE, (AFUNPTR)addHeapRequest,
						   IARG_THREAD_ID, IARG_FUNCARG_ENTRYPOINT_VALUE, 0,
						   IARG_ADDRINT, 1, IARG_END);
			RTN_InsertCall(mallocRtn, IPOINT_AFTER, (AFUNPTR)addHeapMap,
						   IARG_THREAD_ID, IARG_FUNCRET_EXITPOINT_VALUE,
						   IARG_END);
			RTN_Close(mallocRtn);
		}
	}

	{	// look for calloc
		RTN callocRtn = RTN_FindByName(img, "calloc");
		if (RTN_Valid(callocRtn))
		{
			RTN_Open(callocRtn);
			// Instrument to print the input argument values: numElemt, sizeElemt
			// and the return value (memory location allocated)
			RTN_InsertCall(callocRtn, IPOINT_BEFORE, (AFUNPTR)addHeapRequest,
						   IARG_THREAD_ID, IARG_FUNCARG_ENTRYPOINT_VALUE, 0,
						   IARG_FUNCARG_ENTRYPOINT_VALUE, 1, IARG_END);
			RTN_InsertCall(callocRtn, IPOINT_AFTER, (AFUNPTR)addHeapMap,
						   IARG_THREAD_ID, IARG_FUNCRET_EXITPOINT_VALUE,
						   IARG_END);
			RTN_Close(callocRtn);
		}
	}

	{	// look for free
		RTN freeRtn = RTN_FindByName(img, "free");
		if (RTN_Valid(freeRtn))
		{
			RTN_Open(freeRtn);
			// Instrument to print the input argument value (memory location freed)
			RTN_InsertCall(freeRtn, IPOINT_BEFORE, (AFUNPTR)remHeapMap,
						   IARG_THREAD_ID, IARG_FUNCARG_ENTRYPOINT_VALUE, 0,
						   IARG_END);
			RTN_Close(freeRtn);
		}
	}

	// {	// look for realloc
	// 	RTN reallocRtn = RTN_FindByName(img, "realloc");
	// 	if (RTN_Valid(reallocRtn))
	// 	{
	// 		RTN_Open(reallocRtn);
	// 		// Instrument to print the input argument values: origMemory, memRequest
	// 		// and the return value (memory location allocated)
	// 		RTN_InsertCall(reallocRtn, IPOINT_BEFORE, (AFUNPTR)addHeapRequest,
	// 					   IARG_THREAD_ID, IARG_FUNCARG_ENTRYPOINT_VALUE, 0,
	// 					   IARG_FUNCARG_ENTRYPOINT_VALUE, 1, IARG_BOOL, true, IARG_END);
	// 		RTN_InsertCall(reallocRtn, IPOINT_AFTER, (AFUNPTR)addHeapMap,
	// 					   IARG_THREAD_ID, IARG_FUNCRET_EXITPOINT_VALUE,
	// 					   IARG_END);
	// 		RTN_Close(reallocRtn);
	// 	}
	// }
}


/* ROUTINE LEVEL INSTRUMENTATION */

// Looking for POSIX locking mechanisms
VOID Routine (RTN rtn, VOID * v)
{
	int column, line;
	std::string fname;

	// get source information
	ADDRINT rta = RTN_Address(rtn);
	PIN_LockClient();
	PIN_GetSourceLocation(rta, &column, &line, &fname);
	PIN_UnlockClient();

	// instrument only instructions whose source location is available
	// and which aren't from the standard library (/usr check)
	if (fname.length() > 0 && fname.find("/usr") == -1)
	{
		RTN_Open(rtn);

		if (DEBUG)
			std::cout << "ADDING INVP\n";

		// trace function invocation by putting for invP
		// note that we couldn't do it at the call site, where we put callP because this has
		// to happen after the call, but IPOINT_AFTER is invalid for call instruction
		RTN_InsertCall(rtn, IPOINT_BEFORE,
			(AFUNPTR)invP, IARG_THREAD_ID,
			IARG_ADDRINT, rta, IARG_END);

		RTN_Close(rtn);
	}

	// if any of these locking functions is called
	std::string rname = RTN_Name(rtn);
	int pat = -1;
	if (rname == "pthread_mutex_lock@plt")
		pat = 0;
	else if (rname == "sem_wait")
		pat = 1;
	else if (rname == "__pthread_rwlock_rdlock")
		pat = 2;
	else if (rname == "__pthread_rwlock_wrlock")
		pat = 3;

	// call the lock acquisition event handler: lock_func_bf
	if (pat != -1)
	{
		RTN_Open(rtn);

		if (DEBUG)
			std::cout << "ADDING LOCK_BF\n";

		// pass the address of the lock to be acquired using IARG_FUNCARG_ENTRYPOINT_VALUE
		RTN_InsertCall(rtn, IPOINT_BEFORE,
			(AFUNPTR)lock_func_bf,
			IARG_THREAD_ID, IARG_FUNCARG_ENTRYPOINT_VALUE, 0,
			IARG_ADDRINT, pat,
			IARG_END);

		// INS ins = RTN_InsTail(rtn);
		// if (INS_IsRet(ins))
		// RTN_InsertCall(rtn, IPOINT_AFTER,
		// 	(AFUNPTR)lock_func_af,
		// 	IARG_THREAD_ID, IARG_FUNCARG_ENTRYPOINT_VALUE, 0,
		// 	IARG_UINT64, pat, IARG_INST_PTR,
		// 	IARG_END);

		RTN_Close(rtn);
	}

	// if any of the unlocking functions is called
	if (rname == "pthread_mutex_unlock@plt" || rname == "thread_rwlock_unlock" || rname == "sem_post")
	{
		// call the lock release event handler: unlock_func
	 	RTN_Open(rtn);

	 	if (DEBUG)
			std::cout << "ADDING LOCK_AF\n";

		// pass the address of the lock to be released using IARG_FUNCARG_ENTRYPOINT_VALUE
		RTN_InsertCall (rtn, IPOINT_BEFORE,
			(AFUNPTR) unlock_func,
			IARG_THREAD_ID, IARG_FUNCARG_ENTRYPOINT_VALUE, 0,
			IARG_INST_PTR, IARG_END);

		RTN_Close(rtn);
	}
}


/* INSTRUCTION LEVEL INSTRUMENTATION */

// filters and saves instructions to instrument
// We instrument:
// 1. Function Call Events: using callP
// 2. RBP updates (stack set up): using updateRBP
// 3. Function Return Events: using retP
// 4. Memory Access events: using dataman & ptrWrite
VOID Instruction(INS ins, VOID * v)
{
	int column, line;
	std::string fname;

	// get source information
	ADDRINT ina = INS_Address(ins);
	PIN_LockClient();
	PIN_GetSourceLocation(ina, &column, &line, &fname);
	PIN_UnlockClient();

	// instrument only instructions whose source location is available
	// and which aren't from the standard library (/usr check)
	if (fname.length() > 0 && fname.find("/usr") == -1)
	{
		// extract all info
		INSINFO cur(ins, fname, column, line);

		if (DEBUG)
			cur.print(std::cout);

		std::string target = cur.target;
		// if it is a call event, put for callP to trace arguments
		if (target != "")
		{
			int nargs = 0;	// number of arguments

			// find target info to trace call site arguments
			if (funcinfoMap.find(undec(target)) != funcinfoMap.end())
				nargs = funcinfoMap[undec(target)].size() - 2;

			if (DEBUG)
				std::cout << "PUT FOR CALLP\n";

			// if no arguments, pass 0
			if (nargs == 0)
				INS_InsertCall(
				ins, IPOINT_BEFORE, (AFUNPTR)callP,
				IARG_THREAD_ID, IARG_ADDRINT, ina,
				IARG_UINT32, 0, IARG_END);
			else
			{	// else create list of all argument values
				// pass argument values using IARG_FUNCARG_CALLSITE_REFERENCE
				IARGLIST mylist = IARGLIST_Alloc();
				for (int i = 0; i < nargs; ++i)
					IARGLIST_AddArguments(mylist, IARG_FUNCARG_CALLSITE_REFERENCE, i, IARG_END);
				// pass that to the call to callP
				INS_InsertCall(
				ins, IPOINT_BEFORE, (AFUNPTR)callP,
				IARG_THREAD_ID, IARG_ADDRINT, ina,
				IARG_UINT32, nargs, IARG_IARGLIST, mylist,
				IARG_END);
				IARGLIST_Free(mylist);
			}

			// add to list of instrumented instructions
			if (inslist.find(ina) == inslist.end())
				inslist[ina] = cur;
		}

		// if it updates rbp, it marks setting new stack for a funcation
		// put for updateRBP to update invstack & RBPstack
		int t = cur.rbploc;
		if (t != -1)
		{
			if (DEBUG)
				std::cout << "PUT FOR UPDATERBP\n";

			// Send the updated value of RBP to updateRBP
			INS_InsertCall(
			ins, IPOINT_AFTER, (AFUNPTR)updateRBP,
			IARG_ADDRINT, ina, IARG_THREAD_ID,
			IARG_REG_VALUE, INS_RegW(ins, t),
			IARG_END);

			// add to list of instrumented instructions
			if (inslist.find(ina) == inslist.end())
				inslist[ina] = cur;
		}

		// if it is a return event
		// put for retP to update invstack & RBPstack
		if (INS_IsRet(ins))
		{
			if (DEBUG)
				std::cout << "PUT FOR RETP\n";

			// IARG_FUNCRET_EXITPOINT_REFERENCE is pointer to return value
			INS_InsertCall(
			ins, IPOINT_BEFORE, (AFUNPTR)retP, 
			IARG_THREAD_ID, IARG_INST_PTR, 
			IARG_FUNCRET_EXITPOINT_REFERENCE,
			IARG_END);

			// add to list of instrumented instructions
			if (inslist.find(ina) == inslist.end())
				inslist[ina] = cur;
		}


		// if it is a memory access
		// put for dataman to record memory access
		// we send three memory addresses to dataman:
		// memOp1: for read
		// memOp2: for read2 in case the instruction reads to memory locations
		// memOp3: for write
		if (cur.R || cur.W)
		{
			if (DEBUG)
				std::cout << "PUT FOR DATAMAN\n";

			// if both read and write, like `add` instruction
			// send both addresses
			if (cur.R && cur.W)
			{
				INS_InsertCall(
				ins, IPOINT_BEFORE, (AFUNPTR)dataman,
				IARG_THREAD_ID, IARG_ADDRINT, ina,
				IARG_MEMORYREAD_EA, IARG_ADDRINT, -1, IARG_MEMORYWRITE_EA,
				IARG_END);
			}
			// else, if a memory read
			else if (cur.R)
			{
				// if it has two memory reads, like some compare instructions do
				// send both addresses
				if(INS_HasMemoryRead2(ins))
					INS_InsertCall(
					ins, IPOINT_BEFORE, (AFUNPTR)dataman,
					IARG_THREAD_ID, IARG_ADDRINT, ina,
					IARG_MEMORYREAD_EA, IARG_MEMORYREAD2_EA, IARG_ADDRINT, -1,
					IARG_END);
				// otherwise send other addresses as -1
				else
					INS_InsertCall(
					ins, IPOINT_BEFORE, (AFUNPTR)dataman,
					IARG_THREAD_ID, IARG_ADDRINT, ina,
					IARG_MEMORYREAD_EA, IARG_ADDRINT, -1, IARG_ADDRINT, -1,
					IARG_END);
			}
			// else if it is a memory write
			else if (cur.W)
			{
				// send write address, and other as -1
				INS_InsertCall(
				ins, IPOINT_BEFORE, (AFUNPTR)dataman,
				IARG_THREAD_ID, IARG_ADDRINT, ina,
				IARG_ADDRINT, -1, IARG_ADDRINT, -1, IARG_MEMORYWRITE_EA, 
				IARG_END);

				// also, put for ptrWrite
				// which will print the pointee location, if the variable written is a pointer
				if (DEBUG)
					std::cout << "PUT FOR PTRWRITE\n";

				// This can not be done within dataman because the memory address is only
				// available at IPOINT_BEFORE. But the written value is only available after
				// the instruction has executed, ie at IPOINT_AFTER. So this additional callback
				// is required to trace the value written to the pointer in this instruction
				INS_InsertCall(
				ins, IPOINT_AFTER, (AFUNPTR)ptrWrite,
				IARG_THREAD_ID, IARG_ADDRINT, ina,
				IARG_END);
			}

			// add to list of instrumented instructions
			if (inslist.find(ina) == inslist.end())
				inslist[ina] = cur;
		}

		if (DEBUG)
			std::cout << "\n";
	}
}



/* PIN FINALIZATION */

// close output file on exit
VOID Fini (INT32 code, VOID * v)
{
	outp.close();
}

/* MAIN DRIVER */

int main(int argc, char * argv[])
{
	// Initialize pin & symbol manager
	PIN_Init(argc, argv);
	PIN_InitSymbols();

	if (DEBUG)
		for (int i = 0; i < argc; ++i)
			std::cerr << i << " " << argv[i] << "\n";

	// get the input, runid, outdump
	std::string inp(argv[5]);
	inp = inp.substr(inp.find("=")+1);
	if (inp == "")
		inp = "[None]";
	runid = std::string(argv[6]);
	runid = runid.substr(runid.find("=")+1);
	std::string locf(argv[7]);
	locf = locf.substr(locf.find("=")+1);
	locf = locf.substr(locf.find_last_of("/") + 1, locf.find_last_of(".") - locf.find_last_of("/") - 1);

	// Basic variable initializations
	init(inp, runid, locf);
	// Image level Instrumentation for setting up global variable maps
	IMG_AddInstrumentFunction(ImageLoad, 0);
	// Routine level Instrumentation for locking and invocation events
	RTN_AddInstrumentFunction(Routine, 0);
	// Instruction level Instrumentation for all other events
	INS_AddInstrumentFunction(Instruction, 0);
	// Closing output file at the end
	PIN_AddFiniFunction(Fini, 0);

	// Start the program, never returns
	PIN_StartProgram();

	return 0;
}
