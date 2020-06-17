import csv, operator, collections, pickle
from collections import defaultdict
from nltk.stem import PorterStemmer
import sys
from importlib import reload as reload

reload(sys)

ps = PorterStemmer()
program_domain_dict = defaultdict(list)
all_concept_names = list()

with open(sys.argv[1]) as csvfile:
    readCSV = csv.reader(csvfile, delimiter=',')
    for ind1,row in enumerate(readCSV):
        print(row)
        if ind1 == 0:
            all_concept_names = row[1:]
            continue
        current_concept = row[0].split('(')[0]
        # print(current_concept)
        new_list = [(i,float(x)) for i,x in enumerate(row[1:])]
        new_list.sort(key = lambda x: x[1],reverse=True)
        # print(new_list)

        for similar_concepts in new_list:
            if similar_concepts[1] > 0.75:
                if all_concept_names[similar_concepts[0]]!=current_concept:
                    program_domain_dict[current_concept].append(all_concept_names[similar_concepts[0]])
            else:
                break

for key,value in program_domain_dict.items():
    print(key,value)

pickle.dump( program_domain_dict, open( sys.argv[2], "wb" ) )
