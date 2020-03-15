import xml.etree.ElementTree as ET
import sys, os, csv

# SYS ARGS TO BE FILLED LATER
cfname, clangfname, vocabfile, pdname = None, None, None, None

def getProgramDomainWords():
	f = open(vocabfile, 'r')
	prog_dom_reader = csv.reader(f)
	dom_list = {}
	for row in prog_dom_reader:
		word = row[0].lower()
		dom_list[word] = row[1]
	f.close()
	return dom_list

def getProblemDomainWords():
	f = open(pdname, 'r')
	text = f.read()
	text = text.split("\n")
	dom_list = {}
	for row in text:
		dom_list[row.lower()] = "ProblemDomain"
	f.close()
	return dom_list

def wordSegmentation(word):
	words = word.split("_")
	output = []
	for each in words:
		# Split if there is a change in lower to uppercase.
		# Eg: printArray is split as print, Array
		i = 0
		j = 0
		while j < len(each):
			if j == len(each) - 1:
				output.append(each[i:j + 1])
				i = j + 1
			else:
				if each[j].islower() and each[j+1].isupper():
					output.append(each[i:j + 1])
					i = j + 1
			j += 1
	return output

def joinBySpace(l):
	if len(l) == 0:
		return ""
	ans = ""
	for each in l:
		if each != "":
			ans += each + " "
	return ans[:-1]

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

def findProgramDomainMatches(tokens):
	grams = getGrams(joinBySpace(tokens))
	vocab_dict = getProgramDomainWords()
	output = ""
	for each in grams:
		now = each.lower()
		if now in vocab_dict:
			output += now + " : " + vocab_dict[now] + " | "
	return output[:-3]

def findProblemDomainMatches(tokens):
	prob_dict = getProblemDomainWords()
	output = ""
	for each in tokens:
		now = each.lower()
		if now in prob_dict:
			output += now + " | "
	return output[:-3]

def getAllTags(xmlfname):
	tree = ET.parse(xmlfname)
	elem_list = []
	for elem in tree.iter():
		elem_list.append(elem.tag)
	elem_list = list(set(elem_list))
	return elem_list

def parseXML(xmlfname, cfname, type_tag):
	tree = ET.parse(xmlfname)
	root = tree.getroot()
	data = []
	for each in root.findall(".//" + type_tag):
		dict_now = each.attrib
		if dict_now["spelling"] is None or dict_now["spelling"] == 'None':
			continue
		try:
			location = dict_now["location"]
			if location == None:
				continue
			loc = location[:location.find('[')]
			if loc.endswith(cfname):
                		id = dict_now["id"]
				symbol_now = dict_now["spelling"]
				type_now = dict_now["type"]
				start_line = int(location[location.find('[') + 1 : location.find(']')])
				end_line = dict_now["extent.end"]
				end_line = int(end_line[end_line.find('[') + 1 : end_line.find(']')])
				tokens = wordSegmentation(symbol_now)
				prog_matches = findProgramDomainMatches(tokens)
				prob_matches = findProblemDomainMatches(tokens)
				data.append([symbol_now, type_tag, start_line, end_line, dict_now["type"], joinBySpace(tokens), prog_matches, prob_matches, id])
		except:
			pass
	return data

if __name__ == '__main__':
	if len(sys.argv) != 5:
		print "Give four arguments, src location, clang file, program domain location, problem domain location"
		exit(-1)

	cfname = sys.argv[1]
	clangfname = sys.argv[2]
	vocabfile = sys.argv[3]
	pdname = sys.argv[4]

	tags = getAllTags(clangfname)
	output = []
	for tag in tags:
		data = parseXML(clangfname, cfname, tag)
		output.extend(data)

	(file, ext) = os.path.splitext(cfname)
	f = open(file+"_identifier_commentsXML.csv", 'w')
	writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_NONNUMERIC)
	writer.writerow(["Symbol", "Type", "Start line", "End line", "Data type", "Identifier tokens", "Program Domain matches", "Problem Domain matches", "Symbol id"])
	for each in output:
		writer.writerow(each)
	f.close()