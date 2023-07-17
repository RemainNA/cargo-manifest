import sys
import tkinter as tk
import requests
from ttkHyperlinkLabel import HyperlinkLabel
import myNotebook as nb
from config import config
import json
from os import path

this = sys.modules[__name__]  # For holding module globals

this.cargoDict = {}
this.eddbData = {}
this.inventory = []
this.cargoCapacity = "?"
this.version = 'v2.2.0'

def checkVersion():
	try:
		req = requests.get(url='https://api.github.com/repos/RemainNA/cargo-manifest/releases/latest')
	except:
		return -1
	if not req.status_code == requests.codes.ok:
		return -1 # Error
	data = req.json()
	if data['tag_name'] == this.version:
		return 1 # Newest
	return 0 # Newer version available

def plugin_start3(plugin_dir):
	# Read in item names on startup
	directoryName = path.basename(path.dirname(__file__)) or 'CargoManifest'
	pluginPath = path.join(config.plugin_dir, directoryName)
	filePath = path.join(pluginPath, "items.json")
	this.items = pullItems()
	if this.items == -1:
		# If error reaching EDCD github, use local copy
		this.items = json.loads(open(filePath, 'r').read())
	else:
		# If successful, save local copy
		with open(filePath, 'w') as f:
			f.write(json.dumps(this.items, indent=4, sort_keys=True))
	this.newest = checkVersion()
	return "Cargo Manifest"

def plugin_app(parent):
	# Adds to the main page UI
	this.frame = tk.Frame(parent)
	this.title = tk.Label(this.frame, text="Cargo Manifest")
	this.updateIndicator = HyperlinkLabel(this.frame, text="Update available", anchor=tk.W, url='https://github.com/RemainNA/cargo-manifest/releases')
	this.manifest = tk.Label(this.frame)
	this.title.grid(row = 0, column = 0)
	if this.newest == 0 and not config.get_bool("cm_hideUpdate"):
		this.updateIndicator.grid(padx = 5, row = 0, column = 1)
	return this.frame

def plugin_prefs(parent, cmdr, is_beta):
	# Adds page to settings menu
	frame = nb.Frame(parent)
	this.hideUpdate = tk.BooleanVar(value=config.get_bool("cm_hideUpdate"))
	HyperlinkLabel(frame, text="Cargo Manifest {}".format(this.version), background=nb.Label().cget('background'), url="https://github.com/RemainNA/cargo-manifest").grid()
	tk.Checkbutton(frame, text="Hide update available indicator (not recommended)", variable=this.hideUpdate, background=nb.Label().cget('background')).grid()
	return frame

def prefs_changed(cmdr, is_beta):
	# Saves settings
	config.set("cm_hideUpdate", this.hideUpdate.get())
	if this.newest == 0 and not config.get_bool("cm_hideUpdate"):
		this.updateIndicator.grid(padx = 5, row = 0, column = 1)
	else:
		this.updateIndicator.grid_forget()
	update_display()

def pullItems():
	items = {}

	# Fetch commodity data from EDCD github
	try:
		commodities = requests.get('https://raw.githubusercontent.com/EDCD/FDevIDs/master/commodity.csv')
		rareCommodities = requests.get('https://raw.githubusercontent.com/EDCD/FDevIDs/master/rare_commodity.csv')
	except:
		return -1

	if not commodities.status_code == requests.codes.ok or not rareCommodities.status_code == requests.codes.ok:
		return -1 # Error

	for c in commodities.text.split('\n'):
		line = c.strip().split(',')
		if line[0] == 'id' or c == '':
			continue
		items[line[1].lower()] = {'id':line[0], 'category':line[2], 'name':line[3]}

	for c in rareCommodities.text.split('\n'):
		line = c.strip().split(',')
		if line[0] == 'id' or c == '':
			continue
		items[line[1].lower()] = {'id':line[0], 'category':line[3], 'name':line[4]}
	return items

def journal_entry(cmdr, is_beta, system, station, entry, state):
	# Parse journal entries	
	if entry['event'] == 'Cargo':
		# Emitted whenever cargo hold updates
		if state['Cargo'] != this.cargoDict:
			this.cargoDict = state['Cargo']
		if 'Inventory' in entry and entry['Inventory'] != this.inventory:
			this.inventory = entry['Inventory']
		update_display()
	
	elif entry['event'] == 'Loadout' and this.cargoCapacity != entry['CargoCapacity']:
		# Emitted when loadout changes, plugin only cares if the cargo capacity changes
		this.cargoCapacity = entry['CargoCapacity']
		update_display()
	
	elif entry['event'] == 'StartUp':
		# Tries to update display from EDMC stored data when started after the game
		this.cargoDict = state['Cargo']
		try:
			this.inventory = state['CargoJSON']['Inventory'] # Only supported in 4.1.6 on
		except:
			pass
		cargoCap = 0
		for i in state['Modules']:
			if state['Modules'][i]['Item'] == 'int_cargorack_size1_class1':
				cargoCap += 2
			elif state['Modules'][i]['Item'] == 'int_cargorack_size2_class1':
				cargoCap += 4
			elif state['Modules'][i]['Item'] == 'int_cargorack_size3_class1':
				cargoCap += 8
			elif state['Modules'][i]['Item'] == 'int_cargorack_size4_class1':
				cargoCap += 16
			elif state['Modules'][i]['Item'] == 'int_cargorack_size5_class1':
				cargoCap += 32
			elif state['Modules'][i]['Item'] == 'int_cargorack_size6_class1':
				cargoCap += 64
			elif state['Modules'][i]['Item'] == 'int_cargorack_size7_class1':
				cargoCap += 128
			elif state['Modules'][i]['Item'] == 'int_cargorack_size8_class1':
				cargoCap += 256

		this.cargoCapacity = cargoCap
		update_display()

def update_display():
	# When cargo or loadout change update main UI
	manifest = ""
	currentCargo = 0
	cumulativeMaxSell = 0
	for i in this.inventory:
		line = ""
		if i['Name'] in this.items:
			line = "{quant} {name}".format(quant = i['Count'], name=this.items[i['Name']]['name'])
		else:
			line = "{quant} {name}".format(quant = i['Count'], name=(i['Name_Localised'] if 'Name_Localised' in i else i['Name']))
		if 'Stolen' in i and i['Stolen'] > 0:
			line = line+", {} stolen".format(i['Stolen'])
		if 'MissionID' in i:
			line = line+" (Mission)"

		manifest = manifest+"\n"+line
		currentCargo += int(i['Count'])

	if this.inventory == []:
		for i in this.cargoDict:
			manifest = manifest+"\n{quant} {name}".format(name=(this.items[i]['name'] if i in this.items else i), quant=this.cargoDict[i])
			currentCargo += int(this.cargoDict[i])

	if config.get_bool("cm_showMaxSell") and cumulativeMaxSell > 0:
		manifest = manifest+"\n\nTotal max sell: {:,} cr".format(cumulativeMaxSell)
	
	this.title["text"] = "Cargo Manifest ({curr}/{cap})".format(curr = currentCargo, cap = this.cargoCapacity)
	this.manifest["text"] = manifest.strip() # Remove leading newline
	this.title.grid()
	if this.newest == 0:
		this.manifest.grid(columnspan=2)
	else:
		this.manifest.grid()
	if manifest.strip() == "":
		this.manifest.grid_remove()