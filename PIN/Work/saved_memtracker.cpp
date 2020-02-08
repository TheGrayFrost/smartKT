// #include <unistd.h>
// #include <sys/wait.h>
#include "memtracker.h"
#include <map>
#include <fstream>

// major things left to do:
// 1. handling globals
// 2. inspecting why lock_func_af doesn't work on locks
// 3. making function invocation count threadwise
// 4. handling references


std::map <std::string, int> locks;		// mutex -> type
std::map <int, std::string> unlocks;	// type -> mutex name

// std::map <std::string, std::map<int, std::string>> varmap;	// routine -> offset -> variable node id
// ^ now separated from pintool

std::ofstream outp;						// file to write to

// should do routine wise for memory efficiency
std::map <ADDRINT, INSINFO> inslist;					// all instructions

std::map <THREADID, std::map<ADDRINT, int>> syncs;		// thread -> lock address -> mutex type

long long int timeStamp = 0;			// global event timestep

// need to make these two threadwise for correctness
std::map <std::string, std::map<THREADID, int>> invMap;	// function invocation number
ADDRINT RBP;											// current stack base pointer


/*			variables in stack - need to do later to handle references
std::map <ADDRINT, std::string> stackMap; // address -> variable node id
std::map <ADDRINT, std::pair<std::string, int offset>> stackMap;	// address -> routine x offset
// ^ maybe a better implementation as it decouples varmap from pintool
std::vector <std::pair <ADDRINT, std::pair <std::string, int>>> stackMap;
// ^ also a possible implementation: sorted list of RBP x RoutineName x InvocationNo
// ^ possibly the best way to do it
*/


// basic initialization
VOID init(std::string locf)
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

	// open the output file
	std::string opfile = locf + ".dump";
	outp.open(opfile.c_str());
}

// update rbp on change
VOID updateRBP (ADDRINT rbpval) {RBP = rbpval;}


// memory access event handler
VOID dataman (THREADID tid, ADDRINT ina, ADDRINT memOp)
{
	inslist[ina].memOp = memOp;		// set target memory address - helps in debugging later
	ADDRINT offset = RBP - memOp;	// get offset from current RBP

	// inslist[ina].print();

	// print event type
	if (inslist[ina].flag == 'r')
		outp << "READ ";
	else if (inslist[ina].flag == 'w')
		outp << "WRITE ";
	outp << "THREADID " << tid << " ";						// print thread id
	outp << "FUNCNAME " << inslist[ina].rtnName << " ";		// function linkage name
	// if (varmap.find(inslist[ina].rtnName) == varmap.end() ||
	// 	varmap[inslist[ina].rtnName].find(offset) == varmap[inslist[ina].rtnName].end())
		outp << "OFFSET " << dec << offset << " ";			// offset
	// else
	// 	outp << "VARID " << varmap[inslist[ina].rtnName][offset] << " ";

	// synchronization info
	outp << "SYNCS ";
	if (syncs.find(tid) != syncs.end())
	{
		outp << syncs[tid].size() << " ";
		for (auto l: syncs[tid])
			outp << "ADDRESS 0x" << hex << l.first << " TYPE " << unlocks[l.second] << " ";
	}
	else
		outp << "ASYNC ";

	outp << "id " << dec << ++timeStamp << " ";						// event timestamp
	outp << "INVNO " << invMap[inslist[ina].rtnName][tid] << "\n";	// function invocation count
}

// funcation call event handler
VOID callP (THREADID tid, ADDRINT ina)
{
	invMap[inslist[ina].target][tid]++;								// one more invocation of target
	outp << "CALL THREADID " << tid << " ";							// event type and thread id
	outp << "CALLERNAME " << inslist[ina].rtnName << " ";			// caller linkage name
	outp << "CALLEENAME " << inslist[ina].target << " ";			// callee linkage name
	outp << "id " << dec << ++timeStamp << " ";						// event timestamp
	outp << "INVNO " << invMap[inslist[ina].rtnName][tid] << "\n";	// function invocation count
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

	if (fname.length() > 0)		// instrument only instructions whose source location is available
	{
		if (inslist.find(ina) == inslist.end())
			inslist[ina] = INSINFO(ins, fname, column, line);	// add to list

		// if it is a call event
		if (inslist[ina].target != "")
			INS_InsertCall(
			ins, IPOINT_BEFORE, (AFUNPTR)callP,
			IARG_THREAD_ID, IARG_ADDRINT, ina,
			IARG_END);

		// if it updates rbp
		int t = inslist[ina].rbploc;
		if (t != -1)
			INS_InsertCall(
			ins, IPOINT_AFTER, (AFUNPTR)updateRBP,
			IARG_REG_VALUE, INS_RegW(ins, t),
			IARG_END);

		// if it is a memory access
		if (inslist[ina].flag != 'n')
			INS_InsertCall(
			ins, IPOINT_BEFORE, (AFUNPTR)dataman,
			IARG_THREAD_ID, IARG_ADDRINT, ina,
			IARG_MEMORYOP_EA, 0,
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
	outp << "LOCK TID " << tid << " ADDRESS 0x" << hex << addr;					// event record
	outp << " TYPE " << unlocks[type] << " id " << dec << ++timeStamp << "\n";
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
		outp << "UNLOCK TID " << tid << " ADDRESS 0x" << hex << addr;			// event record
		outp << " TYPE " << unlocks[syncs[tid][addr]] << " id " << dec << ++timeStamp << "\n";
		auto loc = syncs[tid].find(addr);				// unset the locks for thread
		syncs[tid].erase(loc);
		if (syncs[tid].size() == 0)						// remove thread from list if it holds no locks
			syncs.erase(syncs.find(tid));
	// }
}

// Looking for POSIX locking mechanisms
VOID Routine (RTN rtn, VOID * v)
{
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
		std::cout << "No such file " << varfile << "\n";
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

	// get the executable name
	std::string u(argv[argc-1]);
	std::string locf = u.substr(u.find_last_of("/") + 1, u.find_last_of(".") - u.find_last_of("/") - 1);
	// basic variable initializations
	init(locf);
	// initMaps(locf);

	RTN_AddInstrumentFunction(Routine, 0);		// Routine level Instrumentation for locking events
	INS_AddInstrumentFunction(Instruction, 0);	// Instruction level Instrumentation for all other events
	PIN_AddFiniFunction(Fini, 0);				// Closing output file at the end
	
	// Start the program, never returns
	PIN_StartProgram();

	return 0;
}
