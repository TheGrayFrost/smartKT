#ifndef __MEMTRACKER_H__
#define __MEMTRACKER_H__

#include "pin.H"
#include <iostream>
#include <string>
#include <vector>
#include <sstream>

// converts integer into string
std::string to_string (long long int u)
{
	std::stringstream ss;
	ss << dec << u;
	return ss.str();
}

// structure to hold instruction information
struct INSINFO
{
	std::string fname;						// file name
	int column, line;						// column and line no.
	std::string rtnName;					// parent routine
	ADDRINT ina;							// instruction address
	std::string diss;						// instruction assembly
	bool R, W;								// R: whether it reads memory, W: whether it writes to memory
	std::vector <std::string> regR, regW;	// registers read from and written to
	ADDRINT memR1, memR2, memW;				// actual memory reference in case R or W are true
											// need two memR's because some instructions
											// read two memory locations
	std::string target;						// if direct branch or call
	int rbploc;								// if it writes to rbp, used to track stack boundary

	INSINFO() {}
	INSINFO(INS&, std::string = "", int = 0, int = 0);
	void print(std::ostream& = std::cout);				// printing to given stream - for debugging
	void shortPrint(std::ostream& = std::cout);			// short description - for debugging
};

// Constructor when location is available
INSINFO::INSINFO(INS& ins, std::string fn, int col, int lno): fname(fn), column(col), line(lno)
{
	rtnName = RTN_FindNameByAddress(INS_Address(ins));			// get routine name
	ina = INS_Address(ins);										// get instruction address

	// disassembly
	diss = INS_Disassemble(ins);
	std::transform(diss.begin(), diss.end(), diss.begin(), ::tolower);

	// memory access flags
	// some register copies used for faster value transfer also trigger memory access
	// thus added check that "ptr" should be present to denote actual variable access
	R = INS_IsMemoryRead(ins) && (diss.find("ptr") != -1);
	W = INS_IsMemoryWrite(ins) && (diss.find("ptr") != -1);

	// registers
	rbploc = -1;
	int rreg = INS_MaxNumRRegs(ins);
	int wreg = INS_MaxNumWRegs(ins);
	for (int i = 0; i < rreg; ++i)
	{
		// collect all read registers
		regR.push_back(REG_StringShort(INS_RegR(ins, i)));
		// segment register accesses trigger memory access that we don't want to trace
		if (REG_is_seg(INS_RegR(ins, i)))
			R = W = false;
	}
	for (int i = 0; i < wreg; ++i)
	{
		std::string regname = REG_StringShort(INS_RegW(ins, i));
		// collect all write registers
		regW.push_back(regname);
		// if rbp is written, this is used to trace stack boundaries
		if (regname == "rbp" &&  INS_IsMov(ins))
			rbploc = i;
		// again, segment register accesses trigger memory access that we don't want to trace
		if (REG_is_seg(INS_RegW(ins, i)))
			R = W = false;
	}

	// set call target if it is a procedure
	target = "";
	if (INS_IsDirectBranchOrCall(ins))
	{
		ADDRINT taddr = INS_DirectBranchOrCallTargetAddress(ins);	// if procedure call
		if (INS_IsProcedureCall(ins))
		{
			target = RTN_FindNameByAddress(taddr);					// set target
			// removing "@plt" from linkage name for functions linked via plt
			target = target.substr(0, target.find("@plt"));
		}
	}

	// initialize memory access holders
	memR1 = memR2 = memW = -1;
}

// simple printers used for debugging
void INSINFO::shortPrint(std::ostream& outf)
{
	outf << fname.substr(fname.length()-12) << ": " << line << "\n"; 
	outf << rtnName << " INS: 0x" << std::hex << ina << std::dec << ": " << diss << " - " << R << W;
	if (memR1 != -1) 
		outf << " R1 0x" << std::hex << memR1 << std::dec;
	if (memR2 != -1) 
		outf << " R2 0x" << std::hex << memR2 << std::dec;
	if (memW != -1) 
		outf << " W 0x" << std::hex << memW << std::dec;
	outf << "\n";
	// outf << "LOCATION: " << fname << ": " << std::dec << line << " ";
	// outf << "FUNCTION: " << rtnName << " ";
	// outf << "INS: 0x" << std::hex << ina << ": " << diss << " - " << flag << "\n";
}

// simple printers used for debugging
void INSINFO::print(std::ostream& outf)
{
	outf << "LOCATION: " << fname << ": " << line << "\n";
	outf << "FUNCTION: " << rtnName << "\n";
	outf << "INS: 0x" << std::hex << ina << std::dec << ": " << diss << " - " << R << W;
	if (memR1 != -1) 
		outf << " R1 0x" << std::hex << memR1 << std::dec;
	if (memR2 != -1) 
		outf << " R2 0x" << std::hex << memR2 << std::dec;
	if (memW != -1) 
		outf << " W 0x" << std::hex << memW << std::dec;
	if (target != "") outf << "\nTARGET: " << target;
	outf << "\nRR: " << regR.size() << " ";
	for (auto l: regR)
		outf << l << " ";
	outf << "\nWR: " << regW.size() << " ";
	for (auto l: regW)
		outf << l << " ";
	if (rbploc != -1)
		outf << "RBP Updated.";
	outf << "\n";
}

// structure to hold function information for one particular invocation
struct fnlog
{
	THREADID tid;		// thread id
	std::string fname;	// function name
	int invNo;			// invocation number within this thread id
	ADDRINT rbp;		// base pointer

	// basic constructors
	fnlog() {;}
	fnlog (std::string fn, THREADID t, int ino, ADDRINT bp) {fname = fn, tid = t, invNo = ino; rbp = bp;}
	
	// short printer for debugging
	void print(std::ostream& outf = std::cout) const 
		{outf << "|" << tid << ":" << fname << ":" << invNo << ":" << rbp << "| ";}
	
	// < operator required to create std::map
	// bool operator < (const fnlog& rhs) const
	// {
	// 	if (tid != rhs.tid) return tid < rhs.tid;
	// 	if (fname != rhs.fname) return fname < rhs.fname;
	// 	return invNo < rhs.invNo;
	// }
};

// structure to hold function information about a variable from static
struct variable
{
	std::string name;	// variable name
	std::string id;		// clang node id
	ssize_t size;		// size of the base type
	std::string fname;	// variable container
	std::string type;	// variable type
	std::string pid;	// variable semantic parent id
	std::string spattr;	// special attribute: storage class type (FUNCSTATIC etc.)

	int nElem;			// number of elements if array
	bool isPtr;			// if it has pointer type

	// simple constructor
	variable() {size = 0; nElem = -1; isPtr = false;}

	// simple print
	void print(std::ostream& outf = std::cout) 
	{
		outf << fname << ": " << type << " - " << name << ": " << id << " " 
			<< spattr << " " << (((signed)(spattr.find("STATIC")) > 0)?fname:"") 
			<< " Ptr: " << isPtr << " nEl: " << nElem << "\n";
	}

	// updates nElem & isPtr on basis of type
	void patch()
	{
		isPtr = false;
		// if "*" in type
		if (type.find("*") != -1)
			isPtr = true;
		
		nElem = -1;
		// if "[]" in type
		int r = type.find("[");
		if (r != -1)
		{
			// get number of elements between []
			int v = type.find("]");
			nElem = std::atoi(type.substr(r+1, type.find("]")-r-1).c_str());
			if (nElem == 0)
				nElem = -1;
		}
	}
};

// structure to hold information from variable search during runtime
struct accessInfo
{
	ADDRINT memOp;	// address of variable
	ADDRINT offset;	// offset from rbp, if local
	variable var;	// static info about variable
	fnlog f;		// function in which it was found, if local
	int elPos;		// element position if it is element within an array
	bool stat;		// whether static storage variable
	std::string accessType;	// type of variable: GLOBAL, LOCAL, FUNCSTATIC etc.
			
	// simple constructors
	accessInfo() {;}
	accessInfo(std::string A, int E, fnlog F, ADDRINT M, ADDRINT O, bool S, variable V)
	{
		accessType = A; memOp = M; offset = O; var = V; f = F; elPos = E; stat = S;
	}
};

// returns demangled name of any symbol
std::string undec(std::string symname) {
	// std::cerr << symname << "->\n" << PIN_UndecorateSymbolName(symname, UNDECORATION_COMPLETE) << "\n";
	return PIN_UndecorateSymbolName(symname, UNDECORATION_COMPLETE);
}

#endif
