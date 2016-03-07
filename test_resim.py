#!/usr/bin/python

#!/usr/bin/python
"""
This script provides resources for simulating a passive neuron model on a
NeuronGeometry
"""

from NeuronGeometry import *
from neuron_readExportedGeometry import HocGeometry
import scipy
import sys
import json


def delete_module(modname, paranoid=None):
  from sys import modules
  try:
    thismod = modules[modname]
  except KeyError:
    raise ValueError(modname)
  these_symbols = dir(thismod)
  if paranoid is not None:
    try:
      paranoid[:]  # sequence support
    except:
      raise ValueError('must supply a finite list for paranoid')
    else:
      these_symbols = paranoid[:]
  del modules[modname]
  for mod in modules.values():
      try:
        delattr(mod, modname)
      except AttributeError:
        pass
      if paranoid is not None:
        for symbol in these_symbols:
          if symbol[:2] == '__':  # ignore special symbols
            continue
          try:
            delattr(mod, symbol)
          except AttributeError:
            pass


###############################################################################
def makeDemoProperties(parameters=None):
  if parameters is None:
    parameters = (100.0, 1.0, 1.29e-3,
                  100.0, 1.0, 2.7e-6,
                  100.0, 1.0, 2.7e-6);
  
  properties = [
    {
      'matchProp' : 'branchOrder',  # soma has branchOrder == 0
      'matchVal' : 0,
      'name' : 'Soma',
      'values' : {
        'Ra' : parameters[0],
        'cm' : parameters[1]
      },
      'channels' : {
        'pas' : {
          'g' : parameters[2],
          'e' : 0.0
        }
      }
    },
    {
      'matchProp' : 'isTerminal',  # tip is not soma, but isTerminal
      'matchVal' : True,
      'name' : 'Tip',
      'values' : {
        'Ra' : parameters[3],
        'cm' : parameters[4]
      },
      'channels' : {
        'pas' : {
          'g' : parameters[5],
          'e' : 0.0
        }
      }
    },
    {
      'matchProp' : None,  # match the remainder
      'matchVal' : None,
      'name' : 'Middle',
      'values' : {
        'Ra' : parameters[6],
        'cm' : parameters[7]
      },
      'channels' : {
        'pas' : {
          'g' : parameters[8],
          'e' : 0.0
        }
      }
    }
  ]
  return properties


###############################################################################
def makeModel(geometry, passiveFile):
  if os.access(passiveFile, os.R_OK):
    with open(passiveFile, 'r') as fIn:
      properties = json.load(fIn)
  else:
    properties = makeDemoProperties()
  
  def _setProperties(segment):
    for neuronSection in properties:
      if 'matchTag' in neuronSection:
        if neuronSection['matchTag'] in segment.tags:
          # this is the default section, match anything:
          segment.tags.add(neuronSection['name'])
          return neuronSection['values'], neuronSection['channels']
        else:
          continue
      elif neuronSection['matchProp'] is None:
        # this is the default section, match anything:
        segment.tags.add(neuronSection['name'])
        return neuronSection['values'], neuronSection['channels']
      segmentVal = getattr(segment, neuronSection['matchProp'])
      if (hasattr(neuronSection['matchVal'], "__len__") and
          segmentVal in neuronSection['matchVal']) or\
         segmentVal == neuronSection['matchVal']:
        # this section matches segment's properties, so return it
        segment.tags.add(neuronSection['name'])
        return neuronSection['values'], neuronSection['channels']
    raise RuntimeError('No match for segment')
    
  model = {
    'stimulus' : { 'amplitude' : 1.0, # nA
                   'duration'  : 2000, # ms
                   'delay'     : 100, # ms
                   'segment'  : geometry.soma,
                   'location' : geometry.soma.centroidPosition(mandateTag=
                                                               'Soma')
                   
                 },
    'tFinal'   : 4000, # ms
    'dT'       : 0.2, # ms
    'v0'       : 0.0, # mV
    'properties' : _setProperties
  }
  return model


###############################################################################
def _simulateModel(geometry, model, child_conn=None):
  import neuron
  
  ##-------------------------------------------------------------------------##
  def _createSegment(segment, geometry):
    segName = segment.name
    if '[' in segName and ']' in segName:
      ind1 = segName.index('[')
      ind2 = segName.index(']')
      baseName = segName[:ind1]
      index = int(segName[ind1+1:ind2])
      if index == 0:
        # this is the first time this baseName is used, create all at once
        maxInd = 0
        for seg in geometry.segments:
          if seg.name.startswith(baseName + '['):
            segIndex = int(seg.name[ind1+1:-1])
            maxInd = max(maxInd, segIndex)
        neuron.h('create %s[%d]' % (baseName, maxInd + 1))
      # get the hoc segment object, and add it to NeuronGeometry segment object
      segment.hSeg = getattr(neuron.h, baseName)[index]
    else:
      neuron.h('create %s' % segName)
      segment.hSeg = getattr(neuron.h, segName)
    return segment.hSeg  
  ##-------------------------------------------------------------------------##
  def _getHSeg(segName):
    if '[' in segName and ']' in segName:
      ind1 = segName.index('[')
      ind2 = segName.index(']')
      baseName = segName[:ind1]
      index = int(segName[ind1+1:ind2])
      return getattr(neuron.h, baseName)[index]
    else:
      return getattr(neuron.h, segName)
  ##-------------------------------------------------------------------------##
  def _addGeometryToHoc(geometry):
    # define all the segments within hoc
    for segment in geometry.segments:
      # create the segment, get hoc segment object
      hSeg = _createSegment(segment, geometry)
      # set it as the currently active segment
      hSeg.push()
      # add all the nodes to define the segment geometry
      for node in segment.nodes:
        neuron.h.pt3dadd(node.x, node.y, node.z, 2 * node.r1)
      # no longer editing this segment
      neuron.h.pop_section()
      
    # connect the segments
    for index, segment in enumerate(geometry.segments):
      hSeg = segment.hSeg
      # to avoid repeating the same connections:
      #  find all the nodes with neighbors, and get the neighbor segment indexes
      #  only specify a connetion if index > all neighbor segment indexes
      neighborNodes = { node for location, nLocation, node
                        in segment.neighborLocations }
      connectNodes = []
      for node in neighborNodes:
        neighborInds = [geometry.segments.index(neighbor) for neighbor in
                        node.segments]
        if min(neighborInds) == index:
          # make all the connections
          connectNodes.append(node)
      
      if not connectNodes:
        continue
      
      for neighbor, (location, nLocation, node) in zip(segment.neighbors,
                                                      segment.neighborLocations):
        if node not in connectNodes:
          # don't add this connection now
          continue
        nSeg = neighbor.hSeg
        nSeg.connect(hSeg, location, nLocation)
  ##-------------------------------------------------------------------------##
  def _setProperties(geometry, model):
    
    # first find branch orders, because they can be used to target properties
    if geometry.soma.branchOrder is None:
      geometry.calcBranchOrder(doPlot=False)
    
    for segment in geometry.segments:
      properties, channels = model['properties'](segment)
      hSeg = segment.hSeg
      for prop, val in properties.items():
        setattr(hSeg, prop, val)
      for channel, chanPropDict in channels.items():
        hSeg.insert(channel)
        for prop, val in chanPropDict.items():
          setattr(hSeg, prop + '_' + channel, val)
  ##-------------------------------------------------------------------------##
  def _initStimulusAndRecording(geometry, model):
    # set up the stimulus
    stimInfo = model['stimulus']
    iClamp = neuron.h.IClamp(stimInfo['segment'].hSeg(stimInfo['location']))
    iClamp.amp = stimInfo['amplitude']
    iClamp.dur = stimInfo['duration']
    iClamp.delay = stimInfo['delay']
    
    # record voltage in each segment
    vTraces = {segment.name : neuron.h.Vector()
               for segment in geometry.segments}
    for segment in geometry.segments:
      trace = vTraces[segment.name]
      hSeg = segment.hSeg
      hPos = 0.5 # for now, just record in the middle of all segments
      trace.record(hSeg(hPos)._ref_v, model['dT'])
    
    return iClamp, vTraces
  ##-------------------------------------------------------------------------##
  def _runSimulation(model):
    neuron.h.dt = model['dT']
    neuron.h.finitialize(model['v0'])
    neuron.h.fcurrent()
    tFinal = model['tFinal']
    while neuron.h.t < tFinal:
      neuron.h.fadvance()

  geometry.checkConnectivity(removeDisconnected=True, removeLoops=True)
  firstSeg = geometry.segments[0]
  if hasattr(firstSeg, 'hSeg') and firstSeg.hSeg is not None:
    for segment in geometry.segments:
      segment.hSeg = None
  _addGeometryToHoc(geometry)
  _setProperties(geometry, model)
  iClamp, vTraces = _initStimulusAndRecording(geometry, model)
  _runSimulation(model)
  # convert traces to python arrays
  for segment in geometry.segments:
    vTraces[segment.name] = scipy.array(vTraces[segment.name])
  # create time trace
  #numT = len(vTraces[firstSeg.name])
  numT = len(vTraces[geometry.segments[0].name])
  timeTrace = scipy.array([n * model['dT'] for n in range(numT)])
  
  if child_conn is None:
    return timeTrace, vTraces
  else:
    #return timeTrace, vTraces
    child_conn.send((timeTrace, vTraces))
    child_conn.close()


###############################################################################
def simulateModel(geometry, model):
  from multiprocessing import Pipe, Process
  parent_conn, child_conn = Pipe()
  p = Process(target=_simulateModel, args=(geometry, model, child_conn))
  p.start()
  timeTrace, vTraces = parent_conn.recv()
  p.join()
  return timeTrace, vTraces
  

###############################################################################
  

def _assertListsEqual(L1, L2):
  assert len(L1) == len(L2)
  for elem1, elem2 in zip(L1, L2):
    assert elem1 == elem2

def _assertSimsEqual(timeTraceA, timeTraceB, vTracesA, vTracesB):
  _assertListsEqual(timeTraceA, timeTraceB)
  _assertListsEqual(vTracesA.keys(), vTracesB.keys())
  for key in vTracesA.keys():
    _assertListsEqual(vTracesA[key], vTracesB[key])


def testResim(geometry1, geometry2, model1, model2):
  import time
  # simulation model on geometry1
  t0 = time.time()
  timeTrace1A, vTraces1A = simulateModel(geometry1, model1)
  
  # simulation model on geometry2
  t1 = time.time()
  timeTrace2A, vTraces2A = simulateModel(geometry2, model2)
  
  # simulation model on geometry1
  t2 = time.time()
  timeTrace1B, vTraces1B = simulateModel(geometry1, model1)
  
  # simulation model on geometry2
  t3 = time.time()
  timeTrace2B, vTraces2B = simulateModel(geometry2, model2)
  
  t4 = time.time()
  timeTrace1C, vTraces1C = simulateModel(geometry1, model1)
  t5 = time.time()
  
  _assertSimsEqual(timeTrace1A, timeTrace1B, vTraces1A, vTraces1B)
  _assertSimsEqual(timeTrace2A, timeTrace2B, vTraces2A, vTraces2B)
  _assertSimsEqual(timeTrace1A, timeTrace1C, vTraces1A, vTraces1C)
  
  print('Resim worked')
  print((t3 - t2) / (t1 - t0), (t4 - t3) / (t2 - t1), (t5 - t4) / (t3-t2))
  print('Elapsed time: %g' % (t5 - t0))



###############################################################################
def _parseArguments():
  import argparse
  parser = argparse.ArgumentParser(description=
    "Simulate a neuron with geometry exported in a .hoc file, and passive "
    + "properties specified in a separate json .txt file")
  parser.add_argument("geoFile1", help="file specifying neuron geometry A",
                      type=str)
  parser.add_argument("geoFile2", help="file specifying neuron geometry B",
                      type=str)
  parser.add_argument("passiveFile", nargs="?",
                      default="passive_properties.txt",
                      help="file specifying passive properties", type=str)
  options = parser.parse_args()
  assert options.geoFile1 != options.geoFile2, \
    "geoFile1 and geoFile2 must be different"
  return options


###############################################################################
if __name__ == "__main__":
  # get the geometry file
  options = _parseArguments()
  # create geometry from the file
  geometry1 = HocGeometry(options.geoFile1)
  geometry2 = HocGeometry(options.geoFile2)
  
  # get passive model
  model1 = makeModel(geometry1, options.passiveFile)
  model2 = makeModel(geometry2, options.passiveFile)
  
  testResim(geometry1, geometry2, model1, model2)
  
  #exit
  sys.exit(0)
