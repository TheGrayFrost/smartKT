import csv, operator, collections, pickle
import pandas as pd
from collections import OrderedDict
import nltk
from nltk.stem import PorterStemmer
import sys
from importlib import reload as reload

reload(sys)

ps = PorterStemmer()
name_tokens_dict = dict()

f=pd.read_csv(sys.argv[1])
keep_col = ['phrase','most_sim_1','score_1','most_sim_2','score_2','most_sim_3','score_3','most_sim_4','score_4','most_sim_5','score_5','most_sim_6','score_6','most_sim_7','score_7','most_sim_8','score_8','most_sim_9','score_9','most_sim_10','score_10']
new_f = f[keep_col]
new_f.to_csv(sys.argv[2], index=False)

with open(sys.argv[2]) as csvfile:
    readCSV = csv.reader(csvfile, delimiter=',')
    for ind1,row in enumerate(readCSV):
        if(ind1 == 0):  #skip the first row
            continue

        name_tokens_dict[row[0]] = list()   #store a dictionary for every token for ease of search
        stem_word = str(ps.stem(row[0]))
        if stem_word != row[0] and nltk.pos_tag([stem_word])[0][1] != 'JJ':
            name_tokens_dict[row[0]].append((stem_word,'1'))

        for ind2,word in enumerate(row):
            if(ind2%2==0):
                continue
            stem_similar_word = str(ps.stem(word))

            if word!='' and stem_word != '' and nltk.pos_tag([stem_word])[0][1] != 'JJ' and nltk.pos_tag([word])[0][1] != 'JJ' and word!='many' and stem_word!='many':
                name_tokens_dict[row[0]].append((word,row[ind2+1]))    #store the similar word and it's index
                if stem_similar_word != word:
                    name_tokens_dict[row[0]].append((stem_similar_word,row[ind2+1]))

        name_tokens_dict[row[0]] = sorted(name_tokens_dict[row[0]], key=operator.itemgetter(1), reverse=True)    #list sorted by values

for key in name_tokens_dict:
    print(key)
    print(name_tokens_dict[key])

pickle.dump( name_tokens_dict, open(sys.argv[3], "wb" ) )
