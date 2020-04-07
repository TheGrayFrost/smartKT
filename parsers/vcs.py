# Make a `config.txt` file containing the following things in order
# username
# password
# repo (like: dealii/dealii)

from github import Github
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree
from xml.dom import minidom
import sys, time

if sys.version_info > (3, 0):
	import urllib.request as ul
else:
	import urllib2 as ul

def prettify(elem):
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def parse_content(content):
	content = content.split('\n')
	content = [i[3:].strip() for i in content if (i[:3] == '+++' or i[:3] == '---')]
	content = [i[2:] for i in content if (i[:2]=="a/" or i[:2]=="b/")]
	return list(set(content))

def get_issues(root, repo):
	issues = [i for i in repo.get_issues(state='all')]
	print(len(issues), " issues collected")

	iroot = SubElement(root, "ISSUES")

	for idx, i in enumerate(issues, start=1):
		s = SubElement(iroot, "ISSUE")
		s.set('ID', str(i.id))
		s.set('STATE', i.state.encode('ascii', 'ignore'))
		s.set('TITLE', i.title.encode('ascii', 'ignore'))
		f = SubElement(s, 'FILES')
		pr = i.pull_request
		if pr is not None:
			content = ul.urlopen(pr.diff_url).read()
			files = parse_content(content)
			for file in files:
				temp = SubElement(f, 'FILE')
				temp.set('FILENAME', str(file))
		if idx%100 == 0:
			print(idx, " issues processed out of ", len(issues))
	return root

def get_commits(root, repo):
	commits = [i for i in repo.get_commits()]
	print(len(commits), " commits collected")

	croot = SubElement(root, "COMMITS")

	for idx, c in enumerate(commits, start=1):
		try:
			s = SubElement(croot, "COMMIT")
			s.set('ID', str(c.commit.sha))
			message = [m for m in c.commit.message.split('\n') if len(m) > 0]
			s.set('TITLE',message[0].encode('ascii', 'ignore'))
			s.set('DESCRIPTION', '\n'.join([m.encode('ascii', 'ignore') for m in message[1:]]))
			if c.commit.author is not None and c.commit.author.name is not None:
				s.set('AUTHOR', c.commit.author.name.encode('ascii', 'ignore'))
				if c.commit.author.date is not None:
					s.set('AUTHOR_DATE', str(c.commit.author.date))
			else:
				s.set('AUTHOR', "None")
			if c.commit.committer is not None and c.commit.committer.name is not None:
				s.set('COMMITTER', c.commit.committer.name.encode('ascii', 'ignore'))
				if c.commit.committer.date is not None:
					s.set('COMMITTER_DATE', str(c.commit.committer.date))
			else:
				s.set('COMMITTER', "None")
			f = SubElement(s, 'FILES')
			for file in c.files:
				temp = SubElement(f, 'FILE')
				temp.set('FILENAME', str(file.filename))
			if idx%100 == 0:
				print(idx, " commits processed out of ", len(commits))
		except:
			time.sleep(600)
	return root

def generate_vcs_info(config, output_file):
	username, oauth = config['username'], config['oauth']
	repoURL, project_name = config['repo'], config['project_name']

	g = Github(username, oauth)
	repo = g.get_repo(repoURL)

	# Store the information in XML format
	root = Element('VCS')
	root.set('project_name', project_name)
	root.set('repoURL', repoURL)

	# Get Issues related information
	root = get_issues(root, repo)

	# Get commits related information
	root = get_commits(root, repo)

	s = prettify(root)
	with open(output_file, 'w') as f:
		f.write(s)
	print("XML file has been written to ", filename)