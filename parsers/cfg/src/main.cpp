#include "main.h"

clang::index::CodegenNameGenerator *CNG = NULL;
std::string key("St5D7yHzyE5WRpHRGuGVB6r4t4HK47TRS69Gka7Pfc2d2wArVrmyPtUZbEUxVMrZ");

std::string getLocation(const CFGElement &E, SourceManager &SM, bool isStart) {
	std::string res;
	switch (E.getKind()) {
	 case CFGElement::Kind::Statement:
	 case CFGElement::Kind::CXXRecordTypedCall:
	 case CFGElement::Kind::Constructor: {
	   CFGStmt CS = E.castAs<CFGStmt>();
	   const Stmt *S = CS.getStmt();
		 if(isStart)
			 return S->getBeginLoc().printToString(SM);
		 return S->getEndLoc().printToString(SM);
	   break;
	 }
	 default: {
		 res = std::string("ERROR");
		 break;
	 }
	}
	return res;
}

std::pair<int, int> getLineLocPair(std::string s){
	s = s.substr(s.find(':')+1, s.size());
	int first, second;
	first = stoi(s.substr(0, s.find(':')));
	second = stoi(s.substr(s.find(':')+1, s.size()));
	return std::make_pair(first, second);
}

std::string getExtentString(const CFGBlock &CB, SourceManager &SM, const CFGBlock &Entry, const CFGBlock &Exit){
	std::string ret = "";
	if(&CB == &Entry) {
		return std::string("ENTRY");
	} else if(&CB == &Exit){
		return std::string("EXIT");
	} else {
		std::vector<std::pair<int, int>> rangeLocs;
		for(auto i = CB.begin(); i != CB.end(); i++){
			rangeLocs.push_back(getLineLocPair(getLocation(*i, SM, true)));
			rangeLocs.push_back(getLineLocPair(getLocation(*i, SM, false)));
		}
		if(rangeLocs.size() == 0)
			return "[]";
		sort(rangeLocs.begin(), rangeLocs.end(), [](const std::pair<int, int> &lhs, const std::pair<int, int> &rhs){
			if(lhs.first < rhs.first) return true;
			else if(lhs.first == rhs.first){
				if(lhs.second < lhs.second) return true;
			}
			return false;
		});
		ret = "[" + std::to_string(rangeLocs[0].first) + "," +
			std::to_string(rangeLocs[0].second) + "," +
			std::to_string(rangeLocs[rangeLocs.size()-1].first) + "," +
			std::to_string(rangeLocs[rangeLocs.size()-1].second) + "]" ;
		return ret;
	}
	return ret;
}

std::string getConnections(const CFGBlock &CB){
	std::string s = "";
	if(CB.pred_size() > 0){
		s = "[";
		for(auto i = CB.pred_begin(); i != CB.pred_end(); i++)
				s += std::to_string((*i)->getBlockID()) + ",";
		s[s.size()-1] = ']';
	} else s += "[]";
	if(CB.succ_size() > 0){
		s += " [";
		for(auto i = CB.succ_begin(); i != CB.succ_end(); i++)
			s += std::to_string((*i)->getBlockID()) + ",";
		s[s.size()-1] = ']';
	} else s += " []";
	return s;
}

class MyCallGraph : public CallGraph {
public:
	void print(raw_ostream &os){
		os << this->size() << "\n";
		llvm::ReversePostOrderTraversal<const CallGraph*> RPOT(this);
    for (auto I = RPOT.begin(); I != RPOT.end(); I++) {
      const CallGraphNode *N = *I;
      if (N == this->getRoot()) os << "<root>: [";
      else os << CNG->getName(N->getDecl()) << ": [";
      for(auto CI = N->begin(); CI != N->end(); ++CI) {
        os << CNG->getName((*CI)->getDecl()) << ",";
      }
      os << "]\n";
    }
    os.flush();
	}
};

MyCallGraph CG;

// By implementing RecursiveASTVisitor, we can specify which AST nodes
// we're interested in by overriding relevant methods.
class MyASTVisitor : public RecursiveASTVisitor<MyASTVisitor> {
	public:
		AnalysisDeclContextManager *ADCM;
		MyASTVisitor(ASTContext &C, Rewriter &R) : TheContext(C), TheRewriter(R) {
			this->ADCM = new AnalysisDeclContextManager(TheContext);
		}

		bool VisitStmt(Stmt *s) {
			return true;
		}

		bool VisitFunctionDecl(FunctionDecl *f) {
			// Only function definitions (with bodies), not declarations.
			if (f->hasBody()) {
				Stmt *funcBody = f->getBody();
				std::unique_ptr<CFG> sourceCFG = CFG::buildCFG(f, funcBody, &TheContext, CFG::BuildOptions());

				/* Format of Printing CFG:
					1. <MangledName>
					2. <FileName>
					3. <Number of Blocks>
					4. <BlockID> </ENTRY/EXIT/[StartLine,StartCol,EndLine,EndLoc]>  [pred_blocks] [succ_blocks]
				*/
				std::string s = f->getSourceRange().getBegin().printToString(TheContext.getSourceManager());
				sourceCFG->print(llvm::outs(), LangOptions(), true);
				llvm::outs() << CNG->getName(f) << " " << s.substr(0, s.find(":"))
				<< "\n" << sourceCFG->size() << "\n";
				for(auto i = sourceCFG->begin(); i != sourceCFG->end(); i++){
					llvm::outs() << (*i)->getBlockID() << " "
					 << getExtentString(**i, TheContext.getSourceManager(), sourceCFG->getEntry(), sourceCFG->getExit())
					 << " " << getConnections(**i) << "\n";
				}

				// llvm::outs() << "-----------------------------------------------------" << '\n';
				// std::unique_ptr<LiveVariables> livVar(LiveVariables::computeLiveness(*(this->ADCM->getContext(f)), false));
				// livVar->dumpBlockLiveness(TheContext.getSourceManager());
			}

			return true;
		}

	private:
		ASTContext &TheContext;
		Rewriter &TheRewriter;
};

// Implementation of the ASTConsumer interface for reading an AST produced
// by the Clang parser.
class MyASTConsumer : public ASTConsumer {
	public:
		MyASTConsumer(ASTContext &C, Rewriter &R) : Visitor(C, R) {}

		// Override the method that gets called for each parsed top-level
		// declaration.
		bool HandleTopLevelDecl(DeclGroupRef DR) override {
			for (DeclGroupRef::iterator b = DR.begin(), e = DR.end(); b != e; ++b) {
				// Traverse the declaration using our AST visitor.
				Visitor.TraverseDecl(*b);
				CG.addToCallGraph(*b);
				//(*b)->dump();
			}
			return true;
		}

	private:
		MyASTVisitor Visitor;
};

// For each source file provided to the tool, a new FrontendAction is created.
class MyFrontendAction : public ASTFrontendAction {
	public:
		MyFrontendAction() {}

		std::unique_ptr<ASTConsumer> CreateASTConsumer(CompilerInstance &CI, StringRef file) override {
			TheRewriter.setSourceMgr(CI.getSourceManager(), CI.getLangOpts());
			if(CNG == NULL)
				CNG = new clang::index::CodegenNameGenerator(CI.getASTContext());
			return llvm::make_unique<MyASTConsumer>(CI.getASTContext(), TheRewriter);
		}

	private:
		Rewriter TheRewriter;
};

int main(int argc, const char **argv) {
	CommonOptionsParser op(argc, argv, ToolingSampleCategory);
	ClangTool Tool(op.getCompilations(), op.getSourcePathList());
	// CFG
	llvm::outs() << key << "\n";
	int ret = Tool.run(newFrontendActionFactory<MyFrontendAction>().get());
	// CallGraph
	llvm::outs() << key << "\n";
	CG.print(llvm::outs());
	return ret;
}
