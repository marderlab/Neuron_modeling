from neuron import *
import string
import time
from pylab import *
from neuron_readExportedGeometry import * 
import  matplotlib.pyplot as plt
import math

geoFile = '/home/Shen/neuron/836_095_63X_IM_34.hoc' # hoc file name
geometry = HocGeometry(geoFile)       # obtain geometry	
(somaindex,somaposition) = geometry.getSomaIndex()	
(axonindices,axonpositions) = geometry.getAxonIndices()
(tipindices,tippositions) = geometry.getTipIndices()

#def PassiveConnect(infile,stimtip,tipindices):

f = open(geoFile,'r')	# open hoc file

line = [l for l in f]	# get all the lines of the hoc file

f.close

numfilament = 0 # use numfilament to record the number of filaments in the hoc file
for i in range(line.__len__()):
	if line[i].strip().startswith('filament') == True:
		numfilament = numfilament + 1

filamentseg = [ 0 for x in range(numfilament)] # use filamentseg to record the number of segments in each filament

temp_numseg = 0
temp_startseg = 0
temp_endseg = 0
temp_indexfilament = 0
for i in range(line.__len__()):   # this loop block is to assign the numbers of segments in each filament to the variable filamentseg
	if line[i].strip().startswith('pt3dclear') == True: # analyze the texts in the hoc file
		temp_startseg = 1  # indicate if 3-D coordinates blocks  start
		temp_endseg = 0 
	if line[i].strip().startswith('pt3dadd') and temp_startseg == 1:
		temp_numseg = temp_numseg + 1 # count the number of segments in each filament
	if line[i].strip().startswith('}') == True:
		temp_endseg = 1   # indicate if 3-D coordinates blocks end
		temp_startseg = 0
		filamentseg[temp_indexfilament] = temp_numseg
		temp_indexfilament = temp_indexfilament + 1
		temp_numseg = 0 

h('numtree = 0')
h.numtree = numfilament
h('create tree[numtree]')  # creat a sections' tree with total number of filaments using NEURON 

index_tree = 0 
for i in range(line.__len__()): # this loop block is to assign 3-D coordinates and diameters to each section
	if line[i].strip().startswith('filament') == True:

		if index_tree == 0: #  whenever we want to assign values to a section, we should pop the section to the first place
			h.pop_section()
			h.tree[index_tree].push()
		else:  # this step shoud be reduced
			h.pop_section()
			h.tree[index_tree].push()
	if line[i].strip().startswith('}') == True: # follow the index of the tree that we want to assign to;
		index_tree = index_tree +1 
	if line[i].strip().startswith('pt3dadd') == True: # analyze the texts in the hoc file

		temp_line = line[i].strip() 
		temp_line = temp_line.lstrip('pt3dadd')
		temp_line = temp_line.lstrip('(')
		temp_line = temp_line.rstrip(')')
		temp_line = temp_line.split(',')
		if temp_line.__len__() == 5:  # extract the 3-D coordinates and diameters out 
			xposition = temp_line[0]
			yposition = temp_line[1]
			zposition = temp_line[2]
			diam = temp_line[3]
			xposition = string.atof(xposition)  # change strings to double types
			yposition = string.atof(yposition)
			zposition = string.atof(zposition)
			diam = string.atof(diam)
		h.pt3dadd(xposition,yposition,zposition,diam)  # assign values using NEURON
for i in range(line.__len__()):	 # this loop block is to connect daughter sections to parent sections
	if line[i].strip().startswith('connect') == True:  # analyze texts in the hoc file
		temp_line = line[i].strip()
		temp_line = temp_line.lstrip('connect')
		temp_line = temp_line.strip()
		temp_line = temp_line.split(',')
		if temp_line.__len__() == 2: # tease out parameters that belong to daughters or parents
			childindex = str()
			childposition = str()
			parentindex = str()
			parentposition = str() 
			is_childindex = 0
			is_childpos = 0
			is_parentindex = 0
			is_parentpos = 0
			for j in range(len(temp_line[0])): # analyze each sentence of the connections
				if temp_line[0][j] == ']':
					is_childindex = 0
				if temp_line[0][j] == ')':
					is_childpos = 0

				if is_childindex == 1:
					childindex = childindex + temp_line[0][j]
				if is_childpos == 1:
					childposition = childposition + temp_line[0][j]
				if temp_line[0][j] == '[':
					is_childindex = 1
				if temp_line[0][j] == '(':
					is_childpos = 1
			for j in range(len(temp_line[1])): # analyze each sentence of the connections
				if temp_line[1][j] == ']':
					is_parentindex = 0
				if temp_line[1][j] == ')':
					is_parentpos =0

				if is_parentindex == 1:
					parentindex = parentindex + temp_line[1][j]
				if is_parentpos == 1:
					parentposition = parentposition + temp_line[1][j]
				if temp_line[1][j] == '[':
					is_parentindex = 1
				if temp_line[1][j] == '(':
					is_parentpos = 1 
			childindex = string.atoi(childindex)
			childposition = string.atof(childposition)
			parentindex = string.atoi(parentindex)
			parentposition = string.atof(parentposition)
			h.pop_section()
			h.tree[childindex].push() # push the section that we will focus on to the first
			h.tree[childindex].connect(h.tree[parentindex],parentposition,childposition)# connect daughters to parents using NEURON

stim_amp = 1  # set up all the parameters that are needed for simulation of passive properties
stim_dur = 2000 # unit of time is ms
stim_delay = 100
h_tstop = 4000
h.dt = 0.2 # ms
h_vinit = 0 # membrane potential starts from zero
sec_cm = 1 # specific membrane capacitance in unit of uF/cm2
#sec_Ra = 60 
#sec_pas_g = 1

def setparameters(soma_pas_g,dendrite_pas_g,Ra):  # treating leak conductance in the soma and elsewhere independently 
	for sec in h.allsec():
		sec.nseg = 1 # segment number in each section is 1 
		sec.Ra = Ra
		sec.cm = sec_cm
		sec.insert('pas')
	for i in range(numfilament):
		if i == somaindex:
			for sec in h.tree[i]:
				sec.pas.g = soma_pas_g
				sec.pas.e = 0
		else:
			for sec in h.tree[i]:
				sec.pas.g = dendrite_pas_g # siemens per cm2 
				sec.pas.e = 0

def StimRecord(stimtip):

	stim = h.IClamp(0.5, sec=h.tree[stimtip])  # use current clamp onto particular place
	stim.amp = stim_amp  # set up stimulation parameters
	stim.dur = stim_dur
	stim.delay = stim_delay



	vec_hoc = [] 
	for var in range(numfilament):
		vec_hoc.append(h.Vector()) # set up the recording variables in NEURON to record the membrane potential of all tips 
	for var in range(numfilament):
		vec_hoc[var].record(h.tree[var](0.5)._ref_v)  # record membrane voltage changes



	time_vec = h.Vector()
	time_vec.record(h._ref_t)  # record the simulation time

	h.load_file("stdrun.hoc")  # 
	go()   # use the initialization parameters we want; this will be further explained in go() function

	vec = [[0 for j in range(len(time_vec))] for i in range(numfilament)]  # transfer the variables in NEURON out to variables in python for further analysis
	 
	for i in range(numfilament): 
		for j in range(len(time_vec)):
			vec[i][j] = vec_hoc[i][j]
	'''for i in axonindices+tipindices:
		for j in range(time_vec_num):
			vec[i][j] = vec_hoc[i][j]
	for j in range(time_vec_num):
		vec[somaindex][j] = vec_hoc[somaindex][j]'''
	time_vec_num = range(len(time_vec)) # transfer the time variable in NEURON out to the time variable in python
	for i in time_vec_num:
		time_vec_num[i] = i*h.dt
	return time_vec_num, vec
def initialize():
	h.finitialize(h_vinit)  # set the starting membrane potential to h_vinit, which is zero
	h.fcurrent()
def integrate():
	while h.t<h_tstop:
		h.fadvance()
def go():  # necessary procedures if we want to change the initialization of NEURON
	initialize()
	integrate()

def getmaxhist(vec):  # calculate the maximum of membrane potential of all tips
	voltagemax = [ 0 for i in range(numfilament)]
	j = 0
	for i in range(len(voltagemax)):
		voltagemax[j] = max(vec[i])
		j = j+1
	#hist(voltagemax,200)
	#plt.hist(voltagemax,bins=200,cumulative=True)
	return voltagemax 


def plotpotential(time_vec,vec): # plot membrane potential of all tips vs. time
	for i in tipindices:
		plot(time_vec,vec[i])
	return

def getpeaklag(vec): # used to be calculate peak lag, but are obselete because time constants computation is available now
	peak_lag = [0 for i in range(len(vec))]
	for i in tipindices:
		peak_lag[i] = vec[i].index(max(vec[i]))
	peak_soma_lag = peak_lag[somaindex]

	peak_remove_zero = [0 for i in range(len(tipindices))]
	j = 0
	for i in range(len(vec)):
		if peak_lag[i]!=0:
			peak_remove_zero[j] = peak_lag[i]
			j = j+1
	for i in range(len(peak_remove_zero)):
		peak_remove_zero[i] = peak_remove_zero[i] - peak_soma_lag 
	for i in range(len(peak_remove_zero)):
		peak_remove_zero[i] = peak_remove_zero[i]*0.025
		if peak_remove_zero[i] == h_tstop-stim_delay-stim_dur:
			peak_remove_zero[i] = 0
	#plot(peak_remove_zero)
	#hist(peak_remove_zero,200)
	#plt.hist(peak_remove_zero,bins=200,cumulative=True)
	return peak_remove_zero

def DistAndSignalStrengthFromAxon(vec,baseindex,baseposition): # calculate electrotonic lengths of all tips
	pDF = HocPathDistanceFinder(geometry,baseindex,baseposition)
	somafrombase = pDF.distanceTo(somaindex,somaposition)
	tiptobase = [0 for i in range(len(tipindices))]
	for i in range(len(tiptobase)):
		tiptobase[i] = pDF.distanceTo(tipindices[i],tippositions[i])
	voltagemax = [ 0 for i in range(len(tipindices))]
	j = 0
	for i in tipindices:
		voltagemax[j] = max(vec[i])
		j = j+1
	scatter(tiptobase,voltagemax)
