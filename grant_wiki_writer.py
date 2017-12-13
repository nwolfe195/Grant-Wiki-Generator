import logging
import sys
import datetime
import csv
import urllib
import zipfile
import os
from jinja2 import Environment, FileSystemLoader
from redminelib import Redmine
import getpass

orgname = 'BRIGHAM AND WOMEN\'S HOSPITAL'
year = datetime.datetime.now().year
grant_template = 'grant_template.txt'
project_id = 'cdnm-grants-portal'
j2_env = Environment(loader=FileSystemLoader(os.getcwd()), trim_blocks=True)
names = []

def main(argv):
	global username	# Read in username credential
	username = raw_input("Enter username: ")
	global password	# Read in password credential
	password = getpass.getpass()

	global wiki_link	# Set which chanmine to use, default chanmine2
	wiki_link = 'https://%s.bwh.harvard.edu' % argv[0]
	global redmine 	# Initialize redmine api
	redmine = Redmine(wiki_link, username=username, password=password, requests={'verify': False})

	# Initialize loggin
	logging.basicConfig(filename='grant_wiki_writer.log', filemode='w', level=logging.INFO)
	logging.info('Wiki link: %s' % wiki_link)
	logging.info('Year: %s' % year)
	logging.info('Resetting author profiles')

	# Clear each researcher page
	# Clear authors from this year
	week = 99	# Start at higher than possible week to ensure retrieval all data
	while week > 0:	# Constructing filename
		if week > 9:
			filename = 'RePORTER_PRJ_C_FY%d_0%d' % (year, week)
		else:
			filename = 'RePORTER_PRJ_C_FY%d_00%d' % (year, week)
		# Construct full web address path
		path = 'https://exporter.nih.gov/CSVs/final/%s.zip' % filename
		clearProcessPath(path, filename)	# Process current link
		week -= 1	# Deincrement week counter to get the next one

	# Clear authors from previous years
	for i in range(2009,year):	
		filename = 'RePORTER_PRJ_C_FY%d' % i 	# Construct filename
		# Construct full web addess path
		path = 'https://exporter.nih.gov/CSVs/final/%s.zip' % filename
		clearProcessPath(path, filename)	# Process current link

	pageclear()	# Resetting of author pages

	# Create and populate grant pages
	week = 99	# Start at higher than possible week to ensure retrieval of all data
	while week > 0:	# Construct filename
		if week > 9:
			filename = 'RePORTER_PRJ_C_FY%d_0%d' % (year, week)
		else:
			filename = 'RePORTER_PRJ_C_FY%d_00%d' % (year, week)
		# Construct full web address path
		path = 'https://exporter.nih.gov/CSVs/final/%s.zip' % filename
		logging.info('File: %s' % path)
		processPath(path, filename)	# Process current link
		week -= 1	# Deincrement week counter to get the next one
	
	# Get data from previous year
	for i in range(2009,year):
		filename = 'RePORTER_PRJ_C_FY%d' % i 	# Construct filename
		# Construct full web address path
		path = 'https://exporter.nih.gov/CSVs/final/%s.zip' % filename
		logging.info('File: %s' % path)
		processPath(path, filename)	# Process current link

	os.remove('file.zip')	# Delete leftover downloaded file
	logging.info('Complete')

# Retrieve link if valid
def processPath(path, filename):
	try:
		testfile = urllib.URLopener()	# Retrieve URL
		testfile.retrieve(path, 'file.zip')
		zip_ref = zipfile.ZipFile('file.zip', 'r')	# Unzip retrieved file
		zip_ref.extractall(os.getcwd())
		zip_ref.close()
		logging.info('Retrieved %s' % filename)
		processCSV('%s.csv' % filename)	# Process csv
		os.remove('%s.csv' % filename)
	except:
		pass

# Retrieve only Brigham and Women's Hospital grants
def processCSV(path):
	try:
		with open(path, "rb") as csvfile:	# Read in csv file
			datareader = csv.reader(csvfile)
			for row in datareader:	# Iterate through each row (grant)
				if row[24] == orgname:	# Check if grant is for Brigham and Women's hospital
					processGrant(row)	# Process the grant
		logging.info('CSV processed')
	except Exception as e:
		logging.info('CSV processing failed: %s' % e)

# Create grant page, write to wiki, update author wiki	
def processGrant(grant):
	try:
		researchers = grant[29].split(';')[0:-1]	# Get researchers from grant
		researcherLinks = []
		# Format researcher names, for display and link creation
		for i in range(0,len(researchers)):
			researchers[i] = researchers[i].replace('(contact)', '')
			names = map(str.strip, researchers[i].split(','))
			researchers[i] = '%s %s' % (names[1], names[0])
			researcherLinks.append((('%s %s' % (names[1], names[0])).replace('.','')).replace(' ', '_'))
		# Process project terms, for display and link creation
		terms = filter(None, map(str.strip, grant[33].rstrip(';').split(';')))
		terms = [x.lower() for x in terms]
		termLinks = [w.replace(' ', '+') for w in terms]
		# Populate jinja2 template
		grant_data = j2_env.get_template('grant_template.txt').render(
								title=grant[34], 
								researchers_researcherLinks=zip(researchers, researcherLinks),
								abstract=grant[27].split(),
								applicationID=grant[0],
								awardDate=grant[5],
								startDate=grant[31],
								endDate=grant[32],
								terms=terms,
								terms_termLink=zip(terms, termLinks))
		logging.info('Processed %s' % grant[34])
		writeGrant(grant[0], grant_data)	# Write grant information to wiki page

		for i in range(0,len(researchers)):	# Append grant information to each author's page
			researcherAppend(researchers[i], researcherLinks[i], grant[34], grant[0])
	except Exception as e: 
		logging.info('Grant %s processing failed  %s' % (grant[34], e))

# Create grant page using redmine api
def writeGrant(id, grant):
	try:
		redmine.wiki_page.create(project_id=project_id, title=id, text=grant)
	except:
		pass
	logging.info('Grant successfully written to wiki')

# Append grant to researcher page using redmine api
def researcherAppend(name, name_link, title, id):
	try:
		# Retrieve current information from author page
		old_data = redmine.wiki_page.get(
								resource_id=name_link, 
								project_id=project_id).text
		# Write new grant using jinja2 template
		new_grant = j2_env.get_template('author_append_template.txt').render(
								title=title,
								id=id)
		updated_page = '%s\n%s' % (old_data, new_grant) # Create new text to replace author
		redmine.wiki_page.update(	# Upload new text with redmine api
								resource_id=name_link,
								project_id=project_id,
								text=updated_page)
		logging.info('%s updated successfully' % name)
	except Exception as e:
		logging.info('Researcher %s updating failed %s' % (name, e))

# Reset each author's page
def pageclear():
	unique_names = list(set(names))	# Remove duplicate names
	for i in range(0,len(unique_names)):	# Iterate through each researcher
		try:
			name = unique_names[i].replace('_', ' ')	# Format for print
			# Create new author text using jinja2
			new_author = j2_env.get_template('author_new_template.txt').render(
					name=name)
			# Upload new author text using redmine api
			redmine.wiki_page.update(
					resource_id=unique_names[i],
					project_id=project_id, 
					text=new_author)
			logging.info('Reset author %s' % name)
		except Exception as e:
			logging.info('%s reset failed' % name)

# Retrieve link if valid
def clearProcessPath(path, filename):
	try:
		testfile = urllib.URLopener()	# Retrieve URL
		testfile.retrieve(path, 'file.zip')
		zip_ref = zipfile.ZipFile('file.zip', 'r')	# Unpack zip file
		zip_ref.extractall(os.getcwd())
		zip_ref.close()
		logging.info('Processing file %s' % path)
		clearProcessCSV('%s.csv' % filename)	# Process csv file
		try:
			os.remove('%s.csv' % filename)
		except Exception as e:
			print e
	except:
		pass

# Get author names
def clearProcessCSV(path):
	try:
		with open(path, "rb") as csvfile:
			datareader = csv.reader(csvfile)	# Read in csv file
			for row in datareader:
				if row[24] == orgname:	# Retrieve only Brigham and Women's hospital grants
					# Process author names
					authors = map(str.strip, row[29].replace('(contact)','').split(';')[0:-1])
					for i in range(0,len(authors)):
						flnames = map(str.strip, authors[i].split(','))
						name = (('%s %s' % (flnames[1], flnames[0])).replace('.', '').replace(' ', '_'))
					names.append(name)	# Add to list of names
	except Exception as e:
		print e

if __name__ == "__main__":
	main(sys.argv[1:])