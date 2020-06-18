import pickle, operator, sys
from collections import defaultdict

pickle_file1 = sys.argv[1]
pickle_file2 = sys.argv[2]

file_token_count = pickle.load( open( pickle_file1, "rb" ) )		#count of total tokens in each file
token_file_count = pickle.load( open( pickle_file2, "rb" ) )

no_of_files = len(file_token_count.keys())
tf_idf = defaultdict(list)
idf_token = dict()	#constant for every token

for token in token_file_count:
	docs_with_token = len(token_file_count[token].keys())

	if docs_with_token:
		idf_token[token] = ((no_of_files*1.0) / docs_with_token)
	else:
		idf_token[token] = 0


for token in token_file_count:
	for file in file_token_count:
		if file in token_file_count[token]:
			term_freq = (int(token_file_count[token][file],base=10)*1.0) / int(file_token_count[file],base=10)	#parse the literals as int and do float division
		else:
			term_freq = 0

		idf = idf_token[token]
		tf_idf[token].append( (str(file),term_freq*idf) )	#shld i store this as str?

	tf_idf[token].sort(key=operator.itemgetter(1), reverse=True)

pickle.dump( tf_idf, open(sys.argv[3], "wb" ) )
