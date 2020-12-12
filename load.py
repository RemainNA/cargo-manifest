import sys
import tkinter as tk
from config import config
import json
from os import path

this = sys.modules[__name__]  # For holding module globals

this.cargoDict = {}
this.namesDict = {}
this.firstCargoRead = True
this.cargoCapacity = "?"

def plugin_start3(plugin_dir):
	# Read in item names on startup
	pluginPath = path.join(config.plugin_dir, "CargoManifest")
	filePath = path.join(pluginPath, "items.json")
	itemsFile = open(filePath, 'r')
	jsonData = itemsFile.read()
	this.namesDict = json.loads(jsonData)
	return "CargoManifest"

def plugin_stop():
	# Writes all recorded names to the items file
	itemsJSON = json.dumps(this.namesDict, indent=4, sort_keys=True)
	pluginPath = path.join(config.plugin_dir, "CargoManifest")
	filePath = path.join(pluginPath, "items.json")
	itemsFile = open(filePath, 'w')
	itemsFile.write(itemsJSON)

def plugin_app(parent):
	# Adds to the main page UI
	this.frame = tk.Frame(parent)
	this.title = tk.Label(this.frame, text="Cargo Manifest")
	this.title.grid()
	return this.frame

def journal_entry(cmdr, is_beta, system, station, entry, state):
	# Parse journal entries
	if entry['event'] == 'MarketBuy' or entry['event'] == 'MarketSell' or entry['event'] == 'CollectCargo' or entry['event'] == 'EjectCargo':
		# Events tend to contain localised names, helpful for building a dict
		try:
			this.namesDict[entry['Type']] = entry['Type_Localised']
		except:
			this.namesDict[entry['Type']] = entry['Type']
			#This may occur when collecting or ejecting non-commodity items
	
	elif entry['event'] == 'Cargo':
		# Emitted whenever cargo hold updates
		if this.firstCargoRead:
			# Emitted on game start, contains full list of localised names
			for i in entry['Inventory']:
				this.namesDict[i['Name']] = i['Name_Localised']
			this.firstCargoRead = False
		if state['Cargo'] != this.cargoDict:
			this.cargoDict = state['Cargo']
		update_display()
	
	elif entry['event'] == 'Loadout' and this.cargoCapacity != entry['CargoCapacity']:
		# Emitted when loadout changes, plugin only cares if the cargo capacity changes
		this.cargoCapacity = entry['CargoCapacity']
		update_display()
	
	elif entry['event'] == 'ShutDown':
		# Resets tracking first login when the game shuts down while EDMC is running
		this.firstCargoRead = True
	
	elif entry['event'] == 'StartUp':
		# Tries to update display from EDMC stored data when started after the game
		this.cargoDict = state['Cargo']
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
		this.firstCargoRead = False
		update_display()

def update_display():
	# When cargo or loadout change update main UI
	currentCargo = 0
	manifest = ""
	for i in this.cargoDict:
		try:
			manifest = manifest+"\n{quant} {name}".format(name=this.namesDict[i], quant=this.cargoDict[i])
		except:
			manifest = manifest+"\n{quant} {name}".format(name=i, quant=this.cargoDict[i])
		currentCargo += int(this.cargoDict[i])
	this.title["text"] = "Cargo Manifest ({curr}/{cap})".format(curr = currentCargo, cap = this.cargoCapacity)+manifest
	this.title.grid()