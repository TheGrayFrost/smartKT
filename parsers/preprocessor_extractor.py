import sys, re
import csv


filename = sys.argv[1]

def process(line, d):
    category = d.split(' ')[0][1:].strip()
    value = d[d.index(category)+len(category):].strip()
    comments = None
    x = re.search("(/\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/)|(//.*)", value)
    if x is not None:
        comments = value[x.start(): x.end()].strip()
        value = value[:x.start()] + value[x.end():].strip()
    return [line, category, value, comments]

with open(filename, "r") as f:
    data = f.readlines()

data = [(idx+1, d) for idx, d in enumerate(data)]
data = [(line, d.strip()) for line, d in data if len(d.strip()) > 0]
temp = []

i = 0
while i < len(data):
    l, s = data[i]
    while s[-1] == "\\":
        i += 1
        s = s[:-1].strip() + " " + data[i][1]

    temp.append((l, s))
    i += 1

data = temp
data = [process(l, d) for l, d in data if d[0] == "#"]
outfilename = filename.split('.')[0]+"_preprocess.csv"
with open(outfilename, "w") as f:
    writer = csv.writer(f)
    writer.writerows(data)

# ['elif', 'undef', 'ifdef', 'error', 'else', 'if', 'pragma', 'endif', 'ifndef', 'include', 'define']
# print(list(set([d[0] for d in data])))

