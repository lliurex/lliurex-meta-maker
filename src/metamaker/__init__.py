import subprocess
import cmd
import configparser
import os
import shutil
import urllib
import urllib.request
from bs4 import BeautifulSoup
import sys
import mmap
import re
import tempfile
import fileinput

class MetaMaker(cmd.Cmd):
	intro = "Welcome to Lliurex Meta Maker \n"
	prompt = 'LlxMeta: '
	flavours = []
	root = os.getcwd()
	config = None
	seeds = {}
	structure = {}

	def completenames(self,text,*ignores):
		lst = cmd.Cmd.completenames(self,text,*ignores)
		return [a for a in lst if a != 'EOF']

	def loadStructure(self):
		'''
			load on self.structure seeds and depends
			self.structure = {
								"llx-base":[],
								"llx-common":[],
								"llx-desktop":["llx-base","llx-common"]
							}
		'''
		structurefiles = []
		for (dirpath,dirname,filelist) in os.walk(self.root+"/seeds"):
			for seed in filelist:
				if seed.lower() == "structure":
					structurefiles.append(dirpath + "/" + seed)

		for strucfilepath in structurefiles:
			fd = open(strucfilepath,'r')
			content = list(map(str.rstrip,fd.readlines()))
			for line in content:
				seed = line.split(":")
				if len(seed) > 1:
					depends = seed[1].lstrip().split(" ")
					self.structure[seed[0]] = depends if depends != [""] else []

	def loadConfig(self,force=False):
		if self.config == None or force:
			self.config = configparser.ConfigParser(delimiters=":")
			self.config.optionxform = str
			self.config.read(self.root + "/update.cfg")

	def saveConfig(self):
		f = open(self.root + "/update.cfg",'w')
		self.config.write(f)
		f.close()

	def downloadFile(self,orig,dest):
		openwebsite = urllib.request.urlopen(orig)
		soup = BeautifulSoup(openwebsite,'html.parser')
		if orig.endswith('/'):
			orig = orig[:-1]
		filename = orig.rsplit('/',1)[-1]
		blacklistlinks = ['description','parent directory','size','last modified','name','doc/']
		if len(soup.findAll('html')) > 0:
			# Folder
			folder = dest + "/" + filename
			try:
				os.mkdir(folder)
			except Exception as e:
				pass
			for link in soup.findAll('a'):
				if str(link.text).lower() not in blacklistlinks:
					self.downloadFile(orig+"/"+str(link.get('href')),folder)
		else:
			urllib.request.urlretrieve(orig,dest + "/" + filename)
			sys.stdout.write('.')
			sys.stdout.flush()


	def renameSeeds(self,flavour,tempfolder):
		baseflavour = flavour.rsplit('.',1)[0]
		basedir = os.path.join(tempfolder,flavour)
		structurefile = os.path.join(basedir,'STRUCTURE')
		seedstorename = []

		if not os.path.exists(structurefile):
			return 0

		#get only seeds exists
		dfstructure = open(structurefile,'r')
		lines = dfstructure.readlines()
		dfstructure.close()
		for line in lines:
			seeds = line.split(":")
			if len(seeds) <= 1:
				continue
			if os.path.exists(os.path.join(basedir,seeds[0])):
				seedstorename.append(seeds[0])

		for seed in seedstorename:
			pathseed = os.path.join(basedir,seed)
			dfstructure = fileinput.FileInput(pathseed,inplace=True)
			for line in dfstructure:
				if re.search(r'^Task:Seeds:',line,re.I):
					for seed in seedstorename:
						line = re.sub(r'(Task-Seeds:)((\s*\w+\s+)*)('+seed+r')(\s+.*|$)',r'\1\2'+baseflavour+r'-\4\5',line,0,re.I)
				print(line,end="")
			dfstructure.close()
			os.rename(pathseed ,os.path.join(basedir,baseflavour+"-"+seed))

		dfstructure = fileinput.FileInput(structurefile,inplace=True)
		for line in dfstructure:
			if len(line.split(":")) <= 1:
				continue
			for seed in seedstorename:
				line = re.sub(r"^"+seed+":",baseflavour+"-"+seed+":",line)
				line = re.sub(r"(\s*)"+seed+r"(\s+|$)",r"\1"+baseflavour+"-"+seed+r"\2",line)
			print(line,end="")
		shutil.move(basedir,self.root + "/seeds/")

	def complete_create(self,text,line,begidx,endidx):
		if len(self.flavours) == 0:
			website = "http://people.canonical.com/~ubuntu-archive/seeds/"
			openwebsite = urllib.request.urlopen(website)
			soup = BeautifulSoup(openwebsite,'html.parser')
			links = soup.findAll('a')[4:]
			for link in links:
				folder = str(link.text)[:-1]
				if not folder.startswith('platform'):
					self.flavours.append(folder)
		return [i for i in self.flavours if i.startswith(text)]

	def downloadPlatformSeed(self,flavour):
		base = flavour.rsplit('.',1)[-1]
		platformurl = "http://people.canonical.com/~ubuntu-archive/seeds/platform."+base
		print("Downloading platform " + base)
		self.downloadFile(platformurl,self.root + "/seeds/")
		print("")

	def downloadFlavourSeed(self,flavour):
		flavoururl = "http://people.canonical.com/~ubuntu-archive/seeds/"+flavour
		tempfolder = tempfile.mkdtemp()
		print("Downloading flavour " + flavour)
		self.downloadFile(flavoururl,tempfolder)
		print("Done")
		print("Renaming seeds")
		self.renameSeeds(flavour,tempfolder)

	def downloadSeeds(self,flavour):
		self.downloadPlatformSeed(flavour)
		self.downloadFlavourSeed(flavour)

	def createNeededStructure(self,codename):
		try:
			os.mkdir(self.root + "/seeds")
			os.mkdir(self.root + "/seeds/lliurex")
		except:
			pass
		f = open(self.root + "/update.cfg",'w')
		f.write("[DEFAULT]\n")
		f.write("dist: "+codename+"\n\n")
		f.write("["+codename+"]\n")
		f.write("seeds:\n")
		f.write("architectures: i386 amd64\n")
		f.write("seed_base: seeds \n")
		f.write("seed_dist: lliurex \n")
		f.write("archive_base/default: http://archive.ubuntu.com/ubuntu http://ppa.launchpad.net/llxdev/"+codename+"/ubuntu\n")
		f.write("components: main restricted universe multiverse\n")
		f.close()
		self.loadConfig(True)


	def newOutputSeeds(self):
		defaultOutSeeds = ["meta-supported","meta-desktop","meta-server","meta-client","meta-infantil","meta-pime","meta-music"]
		answer = input("Use default seeds?([y]/n): ").lower()
		if answer == "" or answer == "y" or answer == "yes":
			dist = self.config.get("DEFAULT","dist")
			self.config.set(dist,"seeds"," ".join(defaultOutSeeds))
			self.saveConfig()

	def loadSeeds(self):
		self.seeds = {}
		for (dirpath,dirname,filelist) in os.walk(self.root+"/seeds"):
			for seed in filelist:
				if seed.lower() != "structure" and dirpath != self.root+"/seeds" :
					self.seeds[seed] = os.path.basename(dirpath) + "/" + seed


	def ensureOutputSeeds(self):
		dist = self.config.get("DEFAULT","dist")
		outputseeds = self.config.get(dist,"seeds")
		for seed in self.config.get(dist,"seeds").strip().split(" "):
			if not seed in self.seeds and seed != "":
				seedpath = self.root + "/seeds/lliurex/"+ seed
				f = open(seedpath,'w')
				f.close()
				self.seeds[seed] = seedpath

	def ensureDebianPackage(self):
		if not os.path.exists('debian'):
			answer = input("Do you want create debian folder?([y]/n): ").lower()
			if answer == "" or answer == "y" or answer == "yes":
				subprocess.call(["dh_make","-s","-n","-p","lliurex-meta_0.1"])
				

	def do_create(self,line):
		'create UbuntuFlavour [LliureXCodeName]'
		args = line.split(" ")
		lliurexcodename = args[1] if len(args) > 1 else args[0].rsplit('.',1)[-1]
		self.createNeededStructure(lliurexcodename)
		self.downloadSeeds(args[0])
		self.newOutputSeeds()
		self.ensureOutputSeeds()
		self.ensureDebianPackage()

	def printDepends(self,id,tabs,parent=None):
		depends = self.structure[id]
		parentstr = " ── ( " +str(parent)+" )" if parent != None else ""
		print("  "*tabs + str(id) + parentstr)
		for depend in depends:
			self.printDepends(depend,tabs+1,id)
		

	def complete_structurePrint(self,text,line,begidx,endidx):
		self.loadStructure()
		return [i for i in self.structure.keys() if i.startswith(text)]

	def do_structurePrint(self,line):
		self.loadStructure()
		#import json
		#print(json.dumps(self.structure,indent=4))
		print("")
		if line != "":
			self.printDepends(line,0)
		else:
			for key in self.structure.keys():
		 		self.printDepends(key,0)

	def complete_seedsRdepends(self,text,line,begidx,endidx):
		self.loadStructure()
		return [i for i in self.structure.keys() if i.startswith(text)]

	# def printRdepends(self,id,tabs,parent=None):
	# 	found = False
	# 	for seed in self.structure.keys():
	# 		if id in self.structure[seed]:
	# 			found = True
	# 			parentstr = " ── ( " +str(parent)+" )" if parent != None else ""
	# 			print("  "*(10 - tabs) + str(seed) + parentstr)
	# 			self.printRdepends(seed,tabs+1,seed)
	# 	if found:
	# 		print("")

	def searchRdepends(self,id):
		result = []
		for seed in self.structure.keys():
			if id in self.structure[seed]:
				result.append(seed)
				result += self.searchRdepends(seed)
		return result

	def printRdepends(self,id,tabs,listToPrint,needle,parent=None):
		if id in listToPrint:
			depends = self.structure[id]
			parentstr = " ── ( " +str(parent)+" )" if parent != None else ""
			if not needle in depends:
				print("  "*tabs + str(id) + parentstr)
				for depend in depends:
					self.printRdepends(depend,tabs+1,listToPrint,id)

	def editValuesConfig(self,section,value,editor="vim"):
		if editor == "":
			editor = "vim"
		options = self.config.get(section,value).split("#")
		enabled = options[0].strip().split(" ")
		disabled = options[1].strip().split(" ") if len(options) > 1 else []
		tempfile = '/tmp/.lliurex-meta-maker.tmp'
		f = open(tempfile,'w')
		f.write("############### "+value+" #######################\n")
		f.write("#enabled values\n")
		for en in enabled:
			f.write(en + "\n")
		f.write("\n#disabled values\n")
		for di in disabled:
			f.write(di + "\n")
		f.close()
		subprocess.call([editor,tempfile])
		f = open(tempfile,'r')
		lines = f.readlines()
		enabled = []
		disabled = []
		inenable = True
		for auxline in lines:
			if auxline.lower().startswith("#enabled"):
				inenable = True
				continue
			if auxline.lower().startswith("#disabled"):
				inenable = False
				continue
			if auxline.startswith("#"):
				continue
			if inenable:
				enabled.append(auxline.strip())
			else:
				disabled.append(auxline.strip())
		f.close()
		appenddisabled = "#"+" ".join(disabled) if len(disabled) > 0 else ""
		finalvalue = " ".join(enabled) + appenddisabled
		self.config.set(section,value,finalvalue)


	def do_seedsRdepends(self,line):
		self.loadStructure()
		listToPrint = self.searchRdepends(line)
		for key in self.structure.keys():
		 		self.printRdepends(key,0,listToPrint,line)

	def do_archiveBaseUpdate(self,line):
		self.loadConfig()
		dist = self.config.get("DEFAULT","dist")
		listoptions = self.config.items(dist)
		resultitems = []
		for x in listoptions:
			if x[0].startswith('archive_base'):
				resultitems.append(x[0])
		for x in resultitems:
			self.editValuesConfig(dist,x,line.strip())
		self.saveConfig()

	def complete_seedEdit(self,text,line,begidx,endidx):
		self.loadSeeds()
		return [i for i in self.seeds if i.startswith(text)]

	def do_seedEdit(self,line):
		self.loadSeeds()
		subprocess.call(['vim','seeds/'+self.seeds[line]])

	def do_seedCreate(self,line):
		self.loadSeeds()
		seedname = line.strip()
		if seedname in self.seeds.keys():
			print("\n Error : seed " + seedname + " already exists \n")
		else:
			f = open('seeds/lliurex/'+seedname,'w')
			f.close()
			subprocess.call(['vim','seeds/lliurex/'+seedname])

	def do_seedSearchPackages(self,line):
		self.loadSeeds()
		packagelist = line.split(" ")
		listfinds = {k:[] for k in packagelist}
		for seed in self.seeds:
			f = open('seeds/'+self.seeds[seed],'r+b')
			try:
				mapfile = mmap.mmap(f.fileno(),0)
			except Exception as e:
				continue
			print('seeds/'+self.seeds[seed])
			for needle in packagelist:
				regex = '\*\s*' + needle + '\s*\Z'
				found = re.search(regex.encode(),mapfile)
				if found != None:
					listfinds[needle].append(seed)
		print("Package \t Seed")
		print("======= \t =====")
		for seed in listfinds.keys():
			print(seed,"\t",listfinds[seed])

	def complete_structureEdit(self,text,line,begidx,endidx):
		folders = [d for d in os.listdir('seeds') if os.path.isdir(os.path.join('seeds', d))]
		return [i for i in folders if i.startswith(text)]

	def do_structureEdit(self,line):
		folder = line.strip()
		subprocess.call(['vim','seeds/'+folder+'/STRUCTURE'])

	def do_update(self,line):
		pass


	def do_exit(self,line):
		'Exit'
		return True

	def do_EOF(self, line):
		'Exit'
		return True
