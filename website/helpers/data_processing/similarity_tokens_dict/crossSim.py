import sys
import csv
from nltk.corpus import stopwords
from gensim.models import Word2Vec
from gensim.models.keyedvectors import KeyedVectors
from gensim.test.utils import get_tmpfile
from scipy.spatial.distance import cosine
from gensim.models.callbacks import CallbackAny2Vec

DEBUG = False

class EpochSaver(CallbackAny2Vec):
    '''Callback to save model after each epoch.'''
    def __init__(self):
        self.epoch = 0
        self.cur_time = datetime.datetime.now()

    def on_epoch_begin(self, model):
        print("Epoch #{} start".format(self.epoch),flush=True)
        self.cur_time = datetime.datetime.now()

    def on_epoch_end(self, model):
        print("Epoch #{} end".format(self.epoch),flush=True)
        delta = datetime.datetime.now()-self.cur_time
        print("Time taken : ",delta,flush=True)
        self.epoch += 1


model = Word2Vec.load(sys.argv[1])
model = model.wv
stop_words = set(stopwords.words('english'))

def get_unmatching_word(word):
    if not word in model.wv.vocab:
        if DEBUG:
            print("Word is not in vocabulary:", word)
        return "None"
    else:
        return "Found"

def process_string(s):
    p =[]
    s = s.lower()
    s = s.strip()
    s = s.replace('-',' ').split(' ')
    if '' in s:
        s.remove('')
    temp = s
    for x in temp:
        if x in stop_words:
            s.remove(x)
    for wrd in s:
        if get_unmatching_word(wrd) == "Found":
            p.append(wrd)
    return p


actual = []
words = []
concept = []
most_sim = []

with open(sys.argv[2],'r') as file:
    all_lines = file.readlines()
    counter = 0
    for x in all_lines:
        x = x.strip().split(',')
        actual.append(x[0])
        words.append(process_string(x[0]))
        concept.append(x[1])

def get_label(i,j,score):
    s = str(score)+"_"+str(concept[i]==concept[j])
    return s

with open(sys.argv[3], 'w') as file:
    writer = csv.writer(file)
    header = ['']
    for i in range(len(words)):
        header.append(actual[i])
    writer.writerow(header)

    for i in range(len(words)):
        row_vals = []
        row_vals.append(actual[i]+"("+concept[i]+")")
        if len(words[i]) > 0:
            most_sim_i=model.most_similar(positive=words[i], negative=[], topn=1)
        else:
            continue
        for p in most_sim_i:
            most_sim_i_word =p[0]
        for j in range(len(words)):
            most_sim_j = []
            if len(words[j]) > 0:
                most_sim_j=model.most_similar(positive=words[j], negative=[], topn=1)
            else:
                continue
            for t in most_sim_j:
                most_sim_j_word =t[0]
            score = model.similarity(most_sim_i_word, most_sim_j_word)
            if (actual[i]!=actual[j]):
                if score == 1:
                    score = 0.5+ model.similarity(words[i][0], words[j][0])
            row_vals.append(score)
        writer.writerow(row_vals)
