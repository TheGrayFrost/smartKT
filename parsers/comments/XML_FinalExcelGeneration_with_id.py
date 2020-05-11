import sys, os 
import glob, re
import csv, pickle
from difflib import SequenceMatcher


DEBUG = False

def getProgramDomainWords(fname):
	f = open(fname, 'r')
	prog_dom_reader = csv.reader(f)
	dom_list = {}
	for row in prog_dom_reader:
		word = row[0].lower()
		if word != "":
			dom_list[word] = row[1]
	f.close()
	return dom_list

def getProblemDomainWords(fname):
	f = open(fname, 'r')
	text = f.read()
	text = text.split("\n")
	dom_list = {}
	for row in text:
		if row != "":
			dom_list[row.lower()] = "ProblemDomain"
	f.close()
	return dom_list

def getIdentifierInfo(outputprefix):
	identifier_info = []
	filename = outputprefix+"_identifiers_commentsXML.csv"
	f = open(filename, 'r')
	r = csv.reader(f)
	for each in r:
		identifier_info.append(each)
	f.close()
	return identifier_info

stop_words = ['ourselves', 'hers', 'between', 'yourself', 'but', 'again', 'there', 'about', 'once', 'during', 'out', 'very', 'having', 'with', 'they', 'own', 'an', 'be', 'some', 'its', 'yours', 'such', 'into', 'of', 'most', 'itself', 'other', 'off', 'is', 's', 'am', 'or', 'who', 'as', 'from', 'him', 'each', 'the', 'themselves', 'until', 'below', 'are', 'we', 'these', 'your', 'his', 'through', 'don', 'nor', 'me', 'were', 'her', 'more', 'himself', 'this', 'down', 'should', 'our', 'their', 'above', 'both', 'up', 'to', 'ours', 'had', 'she', 'all', 'no', 'when', 'at', 'any', 'before', 'them', 'same', 'and', 'been', 'have', 'in', 'will', 'on', 'does', 'yourselves', 'then', 'that', 'because', 'what', 'over', 'why', 'so', 'can', 'did', 'not', 'now', 'under', 'he', 'you', 'herself', 'has', 'just', 'where', 'too', 'only', 'myself', 'which', 'those', 'after', 'few', 'whom', 't', 'being', 'theirs', 'my', 'against', 'a', 'by', 'doing', 'it', 'how', 'further', 'was', 'here', 'than']

def removeStopWords(s):
	s.replace('\n', ' ')
	s.replace('\t', ' ')
	s = s.split(" ")
	ans = ""
	for each in s:
		now = each.lower()
		if now in stop_words or now == "":
			continue
		ans += now + " "
	return ans

def getFilteredComment(comment):
	l = ["?", '"', ".", "#", "!", "$", "%", "&", "^", "*", "(", ")", "~", "`", "+", "/", ",", "|", ":", ";", "\n", "\\", "@", "$", "=", ">", "<"]
	for each in l:
		comment = comment.replace(each, " ")
	comment = comment.replace("'", "")
	comment = removeStopWords(comment)
	return comment

def getGrams(text):
	text = text.lower()
	words = text.split(" ")
	out = []
	for each in words:
		if each != "":
			out.append(each)

	words = out
	for i in range(0,len(words)-1):
		now = words[i] + " " + words[i+1]
		out.append(now)

	for i in range(0,len(words)-2):
		now = words[i] + " " + words[i+1] + " " + words[i+2]
		out.append(now)
	return out

def getConceptMatches(comment_text, vocab_loc, probdom_loc):
	vocab_map = getProgramDomainWords(vocab_loc)
	probdom_map = getProblemDomainWords(probdom_loc)
	filetered_comment = getFilteredComment(comment_text)
	tokens = filetered_comment.split(" ")
	grams = getGrams(filetered_comment)
	vocab_matches = []
	prob_matches = []
	for tok in grams:
		if tok in vocab_map:
			vocab_matches.append([tok, vocab_map[tok]])
		if tok in probdom_map:
			prob_matches.append(tok)
	return (vocab_matches, prob_matches, tokens)

def isScopeMatch(sa, sb):
	if sa[0] <= sb[0] and sa[1] >= sb[1]:
		return True
	if sa[0] <= sb[1] and sa[1] >= sb[1]:
		return True
	return False

def similar(a, b):
	return SequenceMatcher(None, a, b).ratio() >= 0.9

def joinByDel(l, d):
	output = ""
	if len(l) == 0:
		return ""
	for i in range(len(l) - 1):
		output += str(l[i]) + d + " "
	output += str(l[-1])
	return output

def constructGraph(fname, outputprefix, vocab_loc, probdom_loc):
	identifier_info = getIdentifierInfo(outputprefix)
	comments = pickle.load(open(outputprefix+"_comments.p", "rb"))
	scopes = pickle.load(open(outputprefix+"_scopes.p", "rb"))
	output = [["File name", "Comment Id", "Comment Text", "Comment Tokens", "Comment scope", "Prog.dom matches (comm.)", "Prob.dom matches (comm.)", "Identifier symbol", "Identifier type", "Identifier tokens", "Identifier scopes", "prog.dom matches (id)", "prob. dom matches (id)", "prog.dom matches (comm+id)", "prob. dom matches (comm+id)", "Symbol ids"]]

	for i in range(len(comments)):
		comment_text = comments[i][0]
		scope_now = scopes[i]
		if DEBUG:
			print("+++ Comment now:", comment_text)
		(vocab_matches, prob_matches, tokens) = getConceptMatches(comment_text, vocab_loc, probdom_loc)
		if DEBUG:
			print("Vocab matches:", vocab_matches)
			print("Prob matches:", prob_matches)


		id_matches_symbol = []
		id_matches_tokens = []
		id_matches_type = []
		id_matches_scope = []
		id_matches_prog = []
		id_matches_prob = []
		id_matches_symbolId = []
		skip_header = False
		for each in identifier_info:
			if each[0] == "":
				continue
			if skip_header == False:
				skip_header = True
				continue
			if isScopeMatch(scope_now, [int(each[2]), int(each[3])]):
				id_matches_symbol.append(each[0])
				id_matches_tokens.append(each[5])
				id_matches_type.append(each[1] + " : " + each[4])
				id_matches_scope.append(joinByDel(each[2:4], ":"))
				id_matches_prog.append(each[6])
				id_matches_prob.append(each[7])
				id_matches_symbolId.append(each[8])

		id_comment_prog_matches = []
		id_comment_prob_matches = []
		for each in id_matches_prog:
			domain_word_now = each.split(" : ")[0]
			for every in vocab_matches:
				if every[0] == domain_word_now and every[0] != "":
					id_comment_prog_matches.append(every[0])
		for each in id_matches_prob:
			for every in prob_matches:
				if every == each and every != "":
					id_comment_prob_matches.append(every[0])


		output.append([fname, i+1, comment_text, joinByDel(tokens, " |||"), joinByDel(scope_now, ":"),
        joinByDel(vocab_matches, " "), joinByDel(prob_matches, " |||"), joinByDel(id_matches_symbol, " |||"),
        joinByDel(id_matches_type, " |||"), joinByDel(id_matches_tokens, " |||"), joinByDel(id_matches_scope, " |||"),
        joinByDel(id_matches_prog, " |||"), joinByDel(id_matches_prob, " |||"), joinByDel(id_comment_prog_matches, " |||"),
        joinByDel(id_comment_prob_matches, " |||"), joinByDel(id_matches_symbolId, " |||")])
	
	# if len(output) > 1:
	outfile = open(outputprefix + "_knowledgeBase_commentsXML.csv", 'w')
	writer = csv.writer(outfile , delimiter = ',', quoting = csv.QUOTE_NONNUMERIC)
	for eachrow in output:
		writer.writerow(eachrow)
	outfile.close()

if len(sys.argv) != 5:
	print("Give 4 arguments: src filename, outputprefix, program domain location, problem domain location in order")
	exit(-1)

constructGraph(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
