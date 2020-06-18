import re

class CreateLists():
	# compiles and stores all the regexes in the 'regex.txt' file in a list 'all_regex'
	def createRegexList(self,RegexFile):

		all_regex = list()

		with open(RegexFile) as rf:
			for line in rf:
				line = line.strip('\n')
				all_regex.append(re.compile(line,re.IGNORECASE))

		rf.close()
		return all_regex
