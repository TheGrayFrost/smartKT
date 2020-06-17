import sys
import csv
from nltk.corpus import stopwords
from gensim.models import Word2Vec
from gensim.models.keyedvectors import KeyedVectors
from gensim.test.utils import get_tmpfile
from gensim.models.callbacks import CallbackAny2Vec

DEBUG = False

class EpochSaver(CallbackAny2Vec):
	'''Callback to save model after each epoch.'''
	def __init__(self):
		self.epoch = 0
		self.cur_time = datetime.datetime.now()

	def on_epoch_begin(self, model):
		# print("Epoch #{} start".format(self.epoch),flush=True)
		self.cur_time = datetime.datetime.now()

	def on_epoch_end(self, model):
		# print("Epoch #{} end".format(self.epoch),flush=True)
		delta = datetime.datetime.now()-self.cur_time
		# print("Time taken : ",delta,flush=True)
		#output_path = get_tmpfile('file_epoch{}.model'.format(self.epoch))
		#model.save(output_path)
		#print("Temp Saved at ",output_path,flush=True)
		self.epoch += 1

#word_vect = KeyedVectors.load_word2vec_format("corpus_book", binary=True)
#model_name = "models/SO_vectors_200.bin"

model_name = sys.argv[2]
model = Word2Vec.load(model_name)
model = model.wv


def get_unmatching_word(word):
    if not word in model.wv.vocab:
        if DEBUG:
            print("Word is not in vocabulary:", word)
        return "None"
    else:
    	return "Found"

    #return model.wv.doesnt_match(words)


stop_words = set(stopwords.words('english'))
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

def manual_work(x):
	if x[:5]=="\"Alph":
		x= "Alpha-beta pruning"
	if x== "PigeonholeSort":
		x= "pigeonhole sort"
	if x== "ExponentialSearch":
		x= "Exponential Search"
	if x== "SublistSearch":
		x= "Sublist Search"
	if x== "UbiquitousBinary Search":
		x= "Ubiquitous Binary Search"
	if x== "UnboundedSearch":
		x= "Unbounded Search"
	if x== "InformedSearch":
		x= "Informed Search"
	if x== "LocalBeam":
		x= "Local Beam"
	return x

actual = []
words = []
matched_words =[]

concept = []

with open(sys.argv[1],'r') as file:
	all_lines = file.readlines()
	counter = 0
	for x in all_lines:
		x = x.strip().split(',')
		x[0] = manual_work(x[0])
		actual.append(x[0])
		words.append(process_string(x[0]))


with open(sys.argv[3], 'w') as file:
	writer = csv.writer(file)
	header = ['phrase']
	for i in range(10):
		header.append("most_sim_"+str(i+1))
		header.append("score_"+str(i+1))
	writer.writerow(header)
	xx = len(words)
	for i in range(xx):
		row_vals = []
		#print (get_unmatching_word(words[i]))
		row_vals.append(actual[i])
		if words[i] != []:
			most_sim = model.most_similar(positive=words[i], negative=[], topn=10)
			for j in most_sim:
				row_vals.append(j[0])
				row_vals.append(j[1])
			writer.writerow(row_vals)
