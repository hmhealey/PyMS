from utils import *
from fileutils import *
from SFmpq import *
from Libs import PCX,FNT,GRP,PAL,TBL,AIBIN,DAT,IScriptBIN

from Tkinter import *
from tkMessageBox import *

import re, os

def loadsettings(program, default={}):
	settings = default
	try:
		settings.update(eval(file(os.path.join(BASE_DIR,'Settings','%s.txt' % program), 'r').read(),{}))
	except IOError, e:
		if e.args[0] != 2:
			raise
	return settings

PYMS_SETTINGS = loadsettings('PyMS',{'remindme':1})

SC_DIR = PYMS_SETTINGS.get('scdir')
if win_reg:
	try:
		h = OpenKey(HKEY_LOCAL_MACHINE, 'SOFTWARE\\Blizzard Entertainment\\Starcraft')
		SC_DIR = QueryValueEx(h, 'InstallPath')[0]
	except:
		pass
	if SC_DIR and not os.path.isdir(SC_DIR):
		SC_DIR = None

def check_update(p):
	if PYMS_SETTINGS['remindme'] == 1 or PYMS_SETTINGS['remindme'] != PyMS_LONG_VERSION:
		try:
			d = urllib.urlopen('http://www.broodwarai.com/PyMS/update.txt').read()
		except:
			return
		if len(d) == 3:
			d = tuple(ord(l) for l in d)
			if PyMS_VERSION < d:
				def callback():
					UpdateDialog(p,'v%s.%s.%s' % d,settings)
				p.after(1, callback)

def loadsize(window, settings, setting, full=False, size=True, position=None):
	geometry = settings.get(setting)
	if geometry:
		w,h,x,y,fullscreen = parse_geometry(geometry)
		if position:
			x,y = position
		if size and w != None and h != None:
			screen_w = window.winfo_screenwidth()
			screen_h = window.winfo_screenheight()
			resizable = window.resizable()
			min_size = window.minsize()
			if x+w > screen_w:
				x = screen_w-w
			if x < 0:
				x = 0
			if w > screen_w and resizable[0] and screen_w > min_size[0]:
				w = screen_w
			if y+h > screen_h:
				y = max(0,screen_h-h)
			if y < 0:
				y = 0
			if h > screen_h and resizable[1] and screen_h > min_size[1]:
				h = screen_h
			window.geometry('%dx%d+%d+%d' % (w,h, x,y))
		else:
			window.geometry('+%d+%d' % (x,y))
		window.update_idletasks()
		if fullscreen:
			try:
				window.wm_state('zoomed')
			except:
				pass

def savesize(window, settings, setting='window', size=True):
	w,h,x,y,f = parse_geometry(window.winfo_geometry())
	if size:
		z = ['','^'][window.wm_state() == 'zoomed']
		if z:
			window.wm_state('normal')
		settings[setting] = '%dx%d+%d+%d%s' % (w,h,x,y,z)
	else:
		settings[setting] = '+%d+%d' % (x,y)

def pprint(obj, depth=0, max=2, dict_sort=False):
	depth += 1
	string = ''
	if isinstance(obj, dict) and max:
		if obj:
			string += '{\\\n'
			keys = obj.keys()
			if dict_sort:
				keys.sort()
			for key in obj:
				string += '%s%s:' % ('\t'*depth, repr(key))
				string += pprint(obj[key], depth, max-1)
			string += '%s},\\\n' % ('\t'*(depth-1))
		else:
			string += '{},\\\n'
	elif isinstance(obj, list) and max:
		if obj:
			string += '[\\\n'
			for item in obj:
				string += ('%s' % ('\t'*depth))
				string += pprint(item, depth, max-1)
			string += '%s],\\\n' % ('\t'*(depth-1))
		else:
			string += '[],\\\n'
	else:
		string += '%s,\\\n' % (repr(obj),)
	if depth == 1:
		return string[:-3]
	return string

class UpdateDialog(PyMSDialog):
	def __init__(self, parent, v, settings=[]):
		self.version = v
		self.settings = settings
		PyMSDialog.__init__(self, parent, 'New Version Found', resizable=(False, False))

	def widgetize(self):
		Label(self, justify=LEFT, anchor=W, text="Your version of PyMS (%s) is older then the current version (%s).\nIt is recommended that you update as soon as possible." % (PyMS_LONG_VERSION,self.version)).pack(pady=5,padx=5)
		f = Frame(self)
		self.remind = IntVar()
		self.remind.set(self.settings.get('remindme',1) == 1 or self.settings.get('remindme') != PyMS_LONG_VERSION)
		Checkbutton(f, text='Remind me later', variable=self.remind).pack(side=LEFT, padx=5)
		Hotlink(f, 'Homepage', self.homepage).pack(side=RIGHT, padx=5)
		f.pack(fill=X, expand=1)
		ok = Button(self, text='Ok', width=10, command=self.ok)
		ok.pack(pady=5)
		return ok

	def homepage(self, e=None):
		webbrowser.open('http://www.broodwarai.com/index.php?page=pyms')

	def ok(self):
		self.settings['remindme'] = [PyMS_LONG_VERSION,1][self.remind.get()]
		try:
			f = file(os.path.join(BASE_DIR,'Settings','PyMS.txt'),'w')
			f.write(pprint(self.settings))
			f.close()
		except:
			pass
		PyMSDialog.ok(self)

class MPQHandler:
	def __init__(self, mpqs=[], listfiles=None):
		self.mpqs = list(mpqs)
		if listfiles == None:
			self.listfiles = [os.path.join(BASE_DIR,'Libs','Data','Listfile.txt')]
		else:
			self.listfiles = listfiles
		self.handles = {}
		self.open = False
		MpqInitialize()

	def clear(self):
		if self.open:
			self.close_mpqs()
		self.mpqs = []

	def add_defaults(self):
		if SC_DIR:
			for f in ['StarDat','BrooDat','Patch_rt']:
				p = os.path.join(SC_DIR, '%s%smpq' % (f,os.extsep))
				if os.path.exists(p) and not p in self.mpqs:
					h = SFileOpenArchive(p)
					if not SFInvalidHandle(h):
						SFileCloseArchive(h)
						self.mpqs.append(p)

	def set_mpqs(self, mpqs):
		if self.open:
			# raise PyMSError('MPQ','Cannot set mpqs when the current mpqs are open.')
			self.close_mpqs()
		self.mpqs = list(mpqs)

	def open_mpqs(self):
		missing = [[],[]]
		if not FOLDER:
			handles = {}
			self.open = True
			for p,m in enumerate(self.mpqs):
				if not os.path.exists(m):
					missing[0].append(m)
					continue
				handles[m] = MpqOpenArchiveForUpdateEx(m, MOAU_OPEN_EXISTING | MOAU_MAINTAIN_LISTFILE)
				if SFInvalidHandle(handles[m]):
					missing[1].append(m)
				elif self.open == True:
					self.open = handles[m]
			self.handles = handles
		return missing

	def missing(self, missing):
		t = ''
		if missing[0]:
			t = 'Could not find:\n\t' + '\n\t'.join(missing[0])
		if missing[1]:
			t += 'Error loading:\n\t' + '\n\t'.join(missing[1])
		return t

	def close_mpqs(self):
		self.open = False
		for h in self.handles.values():
			if not SFInvalidHandle(h):
				MpqCloseUpdatedArchive(h)
		self.handles = {}

	# folder(True)=Get only from folder,folder(None)=Get from either, MPQ first, folder second,folder(False)=Get only from MPQ
	def get_file(self, path, folder=None):
		mpq = path.startswith('MPQ:')
		if mpq:
			op = path
			path = path[4:].split('\\')
		if not FOLDER and not folder and mpq:
			if self.open == False:
				self.open_mpqs()
				close = True
			else:
				close = False
			if self.open and self.open != True:
				f = SFileOpenFileEx(None, '\\'.join(path), SFILE_SEARCH_ALL_OPEN)
				if not SFInvalidHandle(f):
					r = SFileReadFile(f)
					SFileCloseFile(f)
					p = SFile(r[0], '\\'.join(path))
					return p
			if close:
				self.close_mpqs()
		if folder != False:
			if mpq:
				p = os.path.join(BASE_DIR, 'Libs', 'MPQ', *path)
				if os.path.exists(p):
					return open(p, 'rb')
			elif os.path.exists(path):
				return open(path, 'rb')
		if mpq:
			return BadFile(op)
		return BadFile(path)

	def has_file(self, path, folder=None):
		mpq = path.startswith('MPQ:')
		if mpq:
			path = path[4:].split('\\')
		if not FOLDER and not folder and mpq:
			if self.open == False:
				self.open_mpqs()
				close = True
			else:
				close = False
			if self.open and self.open != True:
				f = SFileOpenFileEx(self.open, '\\'.join(path), SFILE_SEARCH_ALL_OPEN)
				if not SFInvalidHandle(f):
					SFileCloseFile(f)
					return True
			if close:
				self.close_mpqs()
		if folder != False:
			if mpq:
				return os.path.exists(os.path.join(BASE_DIR, 'Libs', 'MPQ', *path))
			else:
				return os.path.exists(path)
		return False

	# Type: 0 = structs, 1 = dict
	def list_files(self, type=0, handles=None):
		if type == 1:
			files = {}
		else:
			files = []
		if self.mpqs:
			if handles == None:
				handles = self.handles.values()
			elif isinstance(handles, int):
				handles = [handles]
			if self.open == False:
				self.open_mpqs()
				close = True
			else:
				close = False
			for h in handles:
				for e in SFileListFiles(h, '\r\n'.join(self.listfiles)):
					if e.fileExists:
						if type == 1:
							if not e.fileName in self.files:
								self.files[e.fileName] = {}
							self.files[e.locale] = e
						else:
							files.append(e)
			if close:
				self.close_mpqs()
		return files

class MpqSelect(PyMSDialog):
	def __init__(self, parent, mpqhandler, filetype, search, settings, open_type='Open'):
		self.mpqhandler = mpqhandler
		self.search = StringVar()
		self.search.set(search)
		self.search.trace('w', self.updatesearch)
		self.settings = settings
		self.regex = IntVar()
		self.regex.set(0)
		self.files = []
		self.file = None
		self.resettimer = None
		self.searchtimer = None
		self.open_type = open_type
		PyMSDialog.__init__(self, parent, self.open_type + ' a ' + filetype)

	def widgetize(self):
		listframe = Frame(self, bd=2, relief=SUNKEN)
		scrollbar = Scrollbar(listframe)
		self.listbox = Listbox(listframe, width=35, height=1, bd=0, yscrollcommand=scrollbar.set, exportselection=0, activestyle=DOTBOX)
		bind = [
			('<MouseWheel>', self.scroll),
			('<Home>', lambda a,i=0: self.move(a,i)),
			('<End>', lambda a,i=END: self.move(a,i)),
			('<Shift-Up>', lambda e,i=0: self.movestring(e,i)),
			('<Up>', lambda a,i=-1: self.move(a,i)),
			('<Left>', lambda a,i=-1: self.move(a,i)),
			('<Shift-Down>', lambda e,i=1: self.movestring(e,i)),
			('<Down>', lambda a,i=1: self.move(a,i)),
			('<Right>', lambda a,i=-1: self.move(a,i)),
			('<Prior>', lambda a,i=-10: self.move(a,i)),
			('<Next>', lambda a,i=10: self.move(a,i)),
		]
		for b in bind:
			listframe.bind(*b)
		scrollbar.config(command=self.listbox.yview)
		scrollbar.pack(side=RIGHT, fill=Y)
		self.listbox.pack(side=LEFT, fill=BOTH, expand=1)
		listframe.pack(fill=BOTH, padx=1, pady=1, expand=1)
		listframe.focus_set()
		s = Frame(self)
		self.textdrop = TextDropDown(s, self.search, self.settings.get('mpqselecthistory',[])[::-1])
		self.textdrop.entry.c = self.textdrop.entry['bg']
		self.textdrop.pack(side=LEFT, fill=X, padx=1, pady=2)
		self.open = Button(s, text=self.open_type, width=10, command=self.ok)
		self.open.pack(side=RIGHT, padx=1, pady=3)
		s.pack(fill=X)
		s = Frame(self)
		Radiobutton(s, text='Wildcard', variable=self.regex, value=0, command=self.updatelist).pack(side=LEFT, padx=1, pady=2)
		Radiobutton(s, text='Regex', variable=self.regex, value=1, command=self.updatelist).pack(side=LEFT, padx=1, pady=2)
		Button(s, text='Cancel', width=10, command=self.cancel).pack(side=RIGHT, padx=1, pady=3)
		s.pack(fill=X)

		self.listfiles()
		self.updatelist()

		if 'mpqselectwindow' in self.settings:
			loadsize(self, self.settings, 'mpqselectwindow', True)

		return self.open

	def scroll(self, e):
		if e.delta > 0:
			self.listbox.yview('scroll', -2, 'units')
		else:
			self.listbox.yview('scroll', 2, 'units')

	def move(self, e, a):
		if a == END:
			a = self.listbox.size()-2
		elif a not in [0,END]:
			a = max(min(self.listbox.size()-1, int(self.listbox.curselection()[0]) + a),0)
		self.listbox.select_clear(0,END)
		self.listbox.select_set(a)
		self.listbox.see(a)

	def listfiles(self):
		filelists = os.path.join(BASE_DIR,'Libs','Data','Listfile.txt')
		self.files = []
		self.mpqhandler.open_mpqs()
		for h in self.mpqhandler.handles.values():
			for e in SFileListFiles(h, filelists):
				if e.fileName and not e.fileName in self.files:
					self.files.append(e.fileName)
		self.mpqhandler.close_mpqs()
		m = os.path.join(BASE_DIR,'Libs','MPQ','')
		for p in os.walk(m):
			folder = p[0].replace(m,'')
			for f in p[2]:
				a = '%s\\%s' % (folder,f)
				if not a in self.files:
					self.files.append(a)
		self.files.sort()

	def updatelist(self):
		if self.searchtimer:
			self.after_cancel(self.searchtimer)
			self.searchtimer = None
		self.listbox.delete(0,END)
		s = self.search.get()
		if not self.regex.get():
			s = '^' + re.escape(s).replace('\\?','.').replace('\\*','.+?') + '$'
		try:
			r = re.compile(s)
		except:
			self.resettimer = self.after(1000, self.updatecolor)
			self.textdrop.entry['bg'] = '#FFB4B4'
		else:
			for f in filter(lambda p: r.match(p), self.files):
				self.listbox.insert(END,f)
		if self.listbox.size():
			self.listbox.select_set(0)
			self.open['state'] = NORMAL
		else:
			self.open['state'] = DISABLED

	def updatecolor(self):
		if self.resettimer:
			self.after_cancel(self.resettimer)
			self.resettimer = None
		self.textdrop.entry['bg'] = self.textdrop.entry.c

	def updatesearch(self, *_):
		if self.searchtimer:
			self.after_cancel(self.searchtimer)
		self.searchtimer = self.after(200, self.updatelist)

	def cancel(self):
		savesize(self, self.settings, 'mpqselectwindow')
		PyMSDialog.ok(self)

	def ok(self):
		savesize(self, self.settings, 'mpqselectwindow')
		f = self.listbox.get(self.listbox.curselection()[0])
		self.file = 'MPQ:' + f
		if not 'mpqselecthistory' in self.settings:
			self.settings['mpqselecthistory'] = []
		if f in self.settings['mpqselecthistory']:
			self.settings['mpqselecthistory'].remove(f)
		self.settings['mpqselecthistory'].append(f)
		if len(self.settings['mpqselecthistory']) > 10:
			del self.settings['mpqselecthistory'][0]
		PyMSDialog.ok(self)

class MPQSettings(Frame):
	def __init__(self, parent, mpqs, settings, setdlg=None):
		if setdlg == None:
			self.setdlg = parent.parent
		else:
			self.setdlg = setdlg
		self.mpqs = list(mpqs)
		self.settings = settings
		Frame.__init__(self, parent)
		Label(self, text='MPQ Settings:', font=('Courier', -12, 'bold'), anchor=W).pack(fill=X)
		Label(self, text="Files will be read from the highest priority MPQ that contains them.\nThe higher an MPQ is on the list the higher its priority.", anchor=W, justify=LEFT).pack(fill=X)
		self.listframe = Frame(self, bd=2, relief=SUNKEN)
		scrollbar = Scrollbar(self.listframe)
		self.listbox = Listbox(self.listframe, width=35, height=1, bd=0, yscrollcommand=scrollbar.set, exportselection=0, activestyle=DOTBOX)
		bind = [
			('<MouseWheel>', self.scroll),
			('<Home>', lambda a,i=0: self.move(a,i)),
			('<End>', lambda a,i=END: self.move(a,i)),
			('<Shift-Up>', lambda e,i=0: self.movestring(e,i)),
			('<Up>', lambda a,i=-1: self.move(a,i)),
			('<Left>', lambda a,i=-1: self.move(a,i)),
			('<Shift-Down>', lambda e,i=1: self.movestring(e,i)),
			('<Down>', lambda a,i=1: self.move(a,i)),
			('<Right>', lambda a,i=-1: self.move(a,i)),
			('<Prior>', lambda a,i=-10: self.move(a,i)),
			('<Next>', lambda a,i=10: self.move(a,i)),
		]
		for b in bind:
			self.listframe.bind(*b)
		scrollbar.config(command=self.listbox.yview)
		scrollbar.pack(side=RIGHT, fill=Y)
		self.listbox.pack(side=LEFT, fill=BOTH, expand=1)
		self.listframe.pack(fill=BOTH, padx=1, pady=1, expand=1)
		for mpq in self.mpqs:
			self.listbox.insert(END,mpq)
		if self.listbox.size():
			self.listbox.select_set(0)

		buttons = [
			('add', self.add, 'Add MPQ (Insert)', NORMAL, 'Insert', LEFT),
			('remove', self.remove, 'Remove MPQ (Delete)', DISABLED, 'Delete', LEFT),
			('opendefault', self.adddefault, "Add default StarCraft MPQ's (Shift+Insert)", NORMAL, 'Shift+Insert', LEFT),
			('up', lambda e=None,i=0: self.movempq(e,i), 'Move MPQ Up (Shift+Up)', DISABLED, 'Shift+Up', RIGHT),
			('down', lambda e=None,i=1: self.movempq(e,i), 'Move MPQ Down (Shift+Down)', DISABLED, 'Shift+Down', RIGHT),
		]
		self.buttons = {}
		toolbar = Frame(self)
		for btn in buttons:
			if isinstance(btn, tuple):
				image = PhotoImage(file=os.path.join(BASE_DIR,'Images','%s.gif' % btn[0]))
				button = Button(toolbar, image=image, width=20, height=20, command=btn[1], state=btn[3])
				button.image = image
				button.tooltip = Tooltip(button, btn[2])
				button.pack(side=btn[5], padx=[0,10][btn[0] == 'opendefault'])
				self.buttons[btn[0]] = button
				a = btn[4]
				if a:
					if not a.startswith('F'):
						self.bind('<%s%s>' % (a[:-1].replace('Ctrl','Control').replace('+','-'), a[-1].lower()), btn[1])
					else:
						self.bind('<%s>' % a, btn[1])
			else:
				Frame(toolbar, width=btn).pack(side=LEFT)
		toolbar.pack(fill=X, padx=51, pady=1)

		self.action_states()

	def activate(self):
		self.listframe.focus_set()

	def action_states(self):
		select = [NORMAL,DISABLED][not self.listbox.curselection()]
		for btn in ['remove','up','down']:
			self.buttons[btn]['state'] = select

	def scroll(self, e):
		if e.delta > 0:
			self.listbox.yview('scroll', -2, 'units')
		else:
			self.listbox.yview('scroll', 2, 'units')

	def move(self, e, a):
		if a == END:
			a = self.listbox.size()-2
		elif a not in [0,END]:
			a = max(min(self.listbox.size()-1, int(self.listbox.curselection()[0]) + a),0)
		self.listbox.select_clear(0,END)
		self.listbox.select_set(a)
		self.listbox.see(a)

	def movempq(self, key=None, dir=0):
		if key and self.buttons[['up','down'][dir]]['state'] != NORMAL:
			return
		i = int(self.listbox.curselection()[0])
		if i == [0,self.listbox.size()-1][dir]:
			return
		s = self.listbox.get(i)
		n = i + [-1,1][dir]
		self.mpqs[i] = self.mpqs[n]
		self.mpqs[n] = s
		self.listbox.delete(i)
		self.listbox.insert(n, s)
		self.listbox.select_clear(0, END)
		self.listbox.select_set(n)
		self.listbox.see(n)
		self.setdlg.edited = True

	def select_files(self):
		path = self.settings.get('lastpath', BASE_DIR)
		file = tkFileDialog.askopenfilename(parent=self, title="Add MPQ's", defaultextension='.mpq', filetypes=[('MPQ Files','*.mpq'),('All Files','*')], initialdir=path, multiple=True)
		if file:
			self.settings['lastpath'] = os.path.dirname(file[0])
		return file

	def add(self, key=None, add=None):
		if add == None:
			n,s = 0,0
			add = self.select_files()
		else:
			n,s = END,self.listbox.size()
		if add:
			error = []
			for i in add:
				if not i in self.mpqs:
					h = SFileOpenArchive(i)
					if not SFInvalidHandle(h):
						SFileCloseFile(h)
						if n == END:
							self.mpqs.append(i)
						else:
							self.mpqs.insert(int(n),i)
						self.listbox.insert(n,i)
			self.listbox.select_clear(0,END)
			self.listbox.select_set(s)
			self.listbox.see(s)
			self.action_states()
			self.setdlg.edited = True

	def remove(self, key=None):
		if key and self.buttons['remove']['state'] != NORMAL:
			return
		i = int(self.listbox.curselection()[0])
		del self.mpqs[i]
		self.listbox.delete(i)
		if self.listbox.size():
			i = min(i,self.listbox.size()-1)
			self.listbox.select_set(i)
			self.listbox.see(i)
		self.action_states()
		self.setdlg.edited = True

	def adddefault(self, key=None):
		global SC_DIR
		scdir = SC_DIR
		if not scdir:
			scdir = tkFileDialog.askdirectory(parent=self, title='Choose StarCraft Directory')
		if scdir and os.path.isdir(scdir):
			a = []
			for f in ['Patch_rt','BrooDat','StarDat']:
				p = os.path.join(scdir, '%s%smpq' % (f,os.extsep))
				if os.path.exists(p) and not p in self.mpqs:
					a.append(p)
			if len(a) == 3 and not SC_DIR:
				SC_DIR = scdir
				PYMS_SETTINGS['scdir'] = SC_DIR
				try:
					f = file(os.path.join(BASE_DIR,'Settings','PyMS.txt'),'w')
					f.write(pprint(PYMS_SETTINGS))
					f.close()
				except:
					pass
			if a:
				self.add(add=a)

class SettingsPanel(Frame):
	types = {
		'PCX':(PCX.PCX,'PCX','pcx',[('StarCraft Special Palette','*.pcx'),('All Files','*')]),
		'FNT':(FNT.FNT,'FNT','fnt',[('StarCraft FNT','*.fnt'),('All Files','*')]),
		'GRP':(GRP.GRP,'GRP','grp',[('StarCraft GRP','*.grp'),('All Files','*')]),
		'CacheGRP':(GRP.CacheGRP,'GRP','grp',[('StarCraft GRP','*.grp'),('All Files','*')]),
		'Palette':(PAL.Palette,'Palette','pal',[('RIFF, JASC, and StarCraft PAL','*.pal'),('StarCraft Tileset WPE','*.wpe'),('ZSoft PCX','*.pcx'),('All Files','*')]),
		'WPE':(PAL.Palette,'Palette','wpe',[('StarCraft Tileset WPE','*.wpe'),('RIFF, JASC, and StarCraft PAL','*.pal'),('ZSoft PCX','*.pcx'),('All Files','*')]),
		'TBL':(TBL.TBL,'TBL','tbl',[('StarCraft TBL Files','*.tbl'),('All Files','*')]),
		'AIBIN':(AIBIN.AIBIN,'aiscript.bin','bin',[('AI Scripts','*.bin'),('All Files','*')]),
		'UnitsDAT':(DAT.UnitsDAT,'units.dat','dat',[('StarCraft DAT files','*.dat'),('All Files','*')]),
		'WeaponsDAT':(DAT.WeaponsDAT,'weapons.dat','dat',[('StarCraft DAT files','*.dat'),('All Files','*')]),
		'FlingyDAT':(DAT.FlingyDAT,'flingy.dat','dat',[('StarCraft DAT files','*.dat'),('All Files','*')]),
		'SpritesDAT':(DAT.SpritesDAT,'sprites.dat','dat',[('StarCraft DAT files','*.dat'),('All Files','*')]),
		'ImagesDAT':(DAT.ImagesDAT,'images.dat','dat',[('StarCraft DAT files','*.dat'),('All Files','*')]),
		'UpgradesDAT':(DAT.UpgradesDAT,'uupgrades.dat','dat',[('StarCraft DAT files','*.dat'),('All Files','*')]),
		'TechDAT':(DAT.TechDAT,'techdata.dat','dat',[('StarCraft DAT files','*.dat'),('All Files','*')]),
		'SoundsDAT':(DAT.SoundsDAT,'sfxdata.dat','dat',[('StarCraft DAT files','*.dat'),('All Files','*')]),
		'IScript':(IScriptBIN.IScriptBIN,'iscript.bin','bin',[('IScripts','*.bin'),('All Files','*')]),
	}

	def __init__(self, parent, entries, settings, mpqhandler, setdlg=None):
		if setdlg == None:
			self.setdlg = parent.parent
		else:
			self.setdlg = setdlg
		self.settings = settings
		self.mpqhandler = mpqhandler
		self.find = PhotoImage(file=os.path.join(BASE_DIR,'Images','find.gif'))
		self.variables = {}
		inmpq = False
		Frame.__init__(self, parent)
		for _ in entries:
			if len(_) == 5:
				f,e,v,t,c = _
			else:
				f,e,v,t = _
				c = None
			self.variables[f] = (IntVar(),StringVar(),[])
			if isinstance(v, tuple) or isinstance(v, list):
				profileKey,valueKey = v
				profile = settings[profileKey]
				v = settings['profiles'][profile][valueKey]
			else:
				v = settings[v]
			m = v.startswith('MPQ:')
			self.variables[f][0].set(m)
			if m:
				self.variables[f][1].set(v[4:])
			else:
				self.variables[f][1].set(v)
			self.variables[f][1].trace('w', self.edited)
			datframe = Frame(self)
			if isstr(e):
				Label(datframe, text=f, font=('Courier', -12, 'bold'), anchor=W).pack(fill=X, expand=1)
				Label(datframe, text=e, anchor=W).pack(fill=X, expand=1)
			elif e:
				Label(datframe, text=f, font=('Courier', -12, 'bold'), anchor=W).pack(fill=X, expand=1)
			else:
				Label(datframe, text=f, anchor=W).pack(fill=X, expand=1)
			entryframe = Frame(datframe)
			e = Entry(entryframe, textvariable=self.variables[f][1], state=DISABLED)
			b = Button(entryframe, image=self.find, width=20, height=20, command=lambda f=f,t=self.types[t],e=e,c=c: self.setting(f,t,e,c))
			self.variables[f][2].extend([e,b])
			if not t == 'Palette':
				inmpq = True
				y = Checkbutton(entryframe, text='', variable=self.variables[f][0])
				self.variables[f][2].append(y)
				y.pack(side=LEFT)
			e.pack(side=LEFT, fill=X, expand=1)
			e.xview(END)
			b.pack(side=LEFT, padx=1)
			entryframe.pack(fill=X, expand=1)
			datframe.pack(side=TOP, fill=X)
		if inmpq:
			Label(self, text='Check the checkbox beside an entry to use a file in the MPQs').pack(fill=X)

	def edited(self, *_):
		if hasattr(self.setdlg, 'edited'):
			self.setdlg.edited = True

	def select_file(self, t, e, f):
		path = self.settings.get('lastpath', BASE_DIR)
		file = tkFileDialog.askopenfilename(parent=self, title="Open a " + t, defaultextension='.' + e, filetypes=f, initialdir=path)
		if file:
			self.settings['lastpath'] = os.path.dirname(file)
		return file

	def setting(self, f, t, e, cb):
		file = ''
		if self.variables[f][0].get():
			m = MpqSelect(self.setdlg, self.mpqhandler, t[1], '*.' + t[2], self.settings)
			if m.file:
				self.mpqhandler.open_mpqs()
				if t[1] == 'FNT':
					file = (self.mpqhandler.get_file(m.file, False),self.mpqhandler.get_file(m.file, True))
				else:
					file = self.mpqhandler.get_file(m.file)
				self.mpqhandler.close_mpqs()
		else:
			file = self.select_file(t[1],t[2],t[3])
		if file:
			c = t[0]()
			if t[1] == 'FNT':
				try:
					c.load_file(file[0])
					self.variables[f][1].set(file[0].file)
				except PyMSError:
					try:
						c.load_file(file[1])
						self.variables[f][1].set(file[0].file)
					except PyMSError, err:
						ErrorDialog(self.setdlg, err)
						return
			else:
				try:
					c.load_file(file)
				except PyMSError, e:
					ErrorDialog(self.setdlg, e)
					return
				self.variables[f][1].set(file)
			e.xview(END)
			if cb:
				cb(c)
			else:
				self.setdlg.edited = True

	def save(self, d, m):
		for s in d[1]:
			self.setdlg.parent.settings[s[2]] = ['','MPQ:'][self.variables[s[0]][0].get()] + self.variables[s[0]][1].get().replace(m,'MPQ:',1)

class SettingsDialog(PyMSDialog):
	def __init__(self, parent, data, min_size, err=None, mpqs=True):
		self.min_size = min_size
		self.data = data
		self.pages = []
		self.err = err
		self.mpqs = mpqs
		self.edited = False
		PyMSDialog.__init__(self, parent, 'Settings')

	def widgetize(self):
		self.minsize(*self.min_size)
		if self.data:
			self.tabs = Notebook(self)
			if self.mpqs:
				self.mpqsettings = MPQSettings(self.tabs, self.parent.mpqhandler.mpqs, self.parent.settings)
				self.tabs.add_tab(self.mpqsettings, 'MPQ Settings')
			for d in self.data:
				if isinstance(d[1],list):
					self.pages.append(SettingsPanel(self.tabs, d[1], self.parent.settings, self.parent.mpqhandler))
				else:
					self.pages.append(d[1](self.tabs))
				self.tabs.add_tab(self.pages[-1], d[0])
			self.tabs.pack(fill=BOTH, expand=1, padx=5, pady=5)
		else:
			self.mpqsettings = MPQSettings(self, self.parent.mpqhandler.mpqs, self.parent.settings, self)
			self.mpqsettings.pack(fill=BOTH, expand=1, padx=5, pady=5)
		btns = Frame(self)
		ok = Button(btns, text='Ok', width=10, command=self.ok)
		ok.pack(side=LEFT, padx=3, pady=3)
		Button(btns, text='Cancel', width=10, command=self.cancel).pack(side=LEFT, padx=3, pady=3)
		btns.pack()
		if 'settingswindow' in self.parent.settings:
			loadsize(self, self.parent.settings, 'settingswindow', True)
		if self.err:
			self.after(1, self.showerr)
		return ok

	def showerr(self):
		ErrorDialog(self, self.err)

	def cancel(self):
		if self.err and askyesno(parent=self, title='Exit?', message="One or more files required for this program can not be found and must be chosen. Canceling will close the program, do you wish to continue?"):
			self.parent.after(1, self.parent.exit)
			PyMSDialog.ok(self)
		elif not self.edited or askyesno(parent=self, title='Cancel?', message="Are you sure you want to cancel?\nAll unsaved changes will be lost."):
			self.parent.settings['settingswindow'] = self.winfo_geometry() + ['','^'][self.wm_state() == 'zoomed']
			PyMSDialog.ok(self)

	def ok(self):
		print self.edited
		if self.edited:
			o = dict(self.parent.settings)
			print self.mpqs, self.mpqsettings.mpqs
			if self.mpqs:
				t = self.parent.mpqhandler.mpqs
				self.parent.mpqhandler.set_mpqs(self.mpqsettings.mpqs)
				self.parent.settings['mpqs'] = self.mpqsettings.mpqs
			m = os.path.join(BASE_DIR,'Libs','MPQ','')
			if self.data:
				for p,d in zip(self.pages,self.data):
					p.save(d,m)
			try:
				e = self.parent.open_files()
			except AttributeError:
				pass
			else:
				if e:
					if self.mpqs:
						self.parent.mpqhandler.set_mpqs(t)
					self.parent.settings = o
					ErrorDialog(self, e)
					return
				self.parent.settings['mpqs'] = self.parent.mpqhandler.mpqs
		savesize(self, self.parent.settings, 'settingswindow')
		PyMSDialog.ok(self)