#!/usr/bin/python



_usageStr=\
"""neuron_writeModelHocFile.py modelName startupFile [paramsFile]
    write a .hoc file that implements a NEURON model with the specified name
  and startup information"""



import sys, os, math
from copy import deepcopy
import neuron_getStartupInfo



###############################################################################
def oneCompartmentPerSegment(startupInfo):
  """
  Alter geometry (if necessary) to enforce one compartment per segment.
  """
  nodes = startupInfo['geometry']['nodes']
  numOldNodes = len(nodes)
  
  oldSegs = startupInfo['geometry']['segments']
  newSegs = []
  for segment in oldSegs:
    if segment['numCompartments'] == 1:
      # no need to change anything
      newSegs.append(segment)
    else:
      oldNumComp = segment['numCompartments']
      for n in range(oldNumComp):
        # make a new segment object
        newSeg = deepcopy(segment)
        newSeg['numCompartments'] = 1
        newSeg['length'] /= oldNumComp
        newSeg['surfaceArea'] /= oldNumComp
        newSeg['volume'] /= oldNumComp
        newSeg['compartmentNums'] = [segment['compartmentNums'][n]]
        newSeg['compartmentNames'] = [segment['compartmentNames'][n]]
        newSeg['name'] += ('Compartment%d' % n)
        # update node structure
        newSegInd = len(newSegs)
        if n > 0:
          # node0 previously created, just update it
          newSeg['node0'] = newSegs[-1]['node1']
          node0 = nodes[newSeg['node0']]
          node0['compartments'].append(newSegInd)
          node0['segments'].append(newSegInd)
        if n < oldNumComp - 1:
          # create a new node1
          newNode = { \
            'x': float('NaN'), \
            'y': float('NaN'), \
            'z': float('NaN'), \
            'segments': [newSegInd], \
            'compartments' : [newSegInd] \
          }
          nodes.append(newNode)
        
        # append newSeg to list of segments
        newSegs.append(newSeg)
    
    # store resulting new segments
    startupInfo['geometry']['segments'] = newSegs
    # update older (not newly-created) nodes
    for n in range(numOldNodes):
      nodes[n]['segments'] = nodes[n]['compartments']



###############################################################################
def _getNodeSide(segment, nodeIndex):
  """
  return an integer describing which side of segment a node is attached to
  """
  if segment['node0'] == nodeIndex:
    return 0
  elif segment['node1'] == nodeIndex:
    return 1
  else:
    raise RuntimeError('Node %d not connected to %s' % \
                       (nodeIndex, segment['name']))



###############################################################################
def _isStateParam(parameter):
  """
  return True if the parameter is a state parameter, False otherwise
  """
  target = parameter['name'].split('_')[0]
  if target in ['v', 'm', 'h'] or \
     target.endswith('Int') or target.endswith('Ext'):
    return True
  else:
    return False



###############################################################################
def _specificity(target, startupInfo, segment=None):
  """
  return an integer rating how specific a parameter is based on its target
  if segment is supplied:
    -the search only tests versus that segment
    -if the parameter doesn't match the segment, specificity is -1
  """

  geometry = startupInfo['geometry']
  if segment:
    # get the specificity relative to reference segment
    
    if target in segment['compartmentNames'][0]:
      # specified compartment, highest specificity
      #   -no tag can be this specific:
      numCompartments = geometry['numCompartments']
      return numCompartments
    elif target in segment['tags']:
      # specified tag, specificity is the number of compartments that DON'T have
      # that tag (i.e. rare tags are specific)
      numCompartments = geometry['numCompartments']
      numTargetTag = geometry['tags'][target]
      return numCompartments - numTargetTag
    else:
      # model-wide or targetting someone else
      for s2 in geometry['segments']:
        if s2 == segment:
          continue
        if target in s2['compartmentNames'][0]:
          # specified other segment, doesn't match
          return -1
      # model-wide parameter
      return 0
  else:
    # get the specificity without a reference segment

    if target in geometry['tags']:
      # specified tag, specificity is the number of compartments that DON'T have
      # that tag (i.e. rare tags are specific)
      numCompartments = geometry['numCompartments']
      numTargetTag = geometry['tags'][target]
      return numCompartments - numTargetTag
    else:
      for s2 in geometry['segments']:
        if target in s2['compartmentNames'][0]:
          # specified compartment, highest specificity
          #   -no tag can be this specific:
          numCompartments = geometry['numCompartments']
          return numCompartments
          
      # model-wide parameter
      return 0



###############################################################################
def _formatParamOutput(name, value, isSegmentParam):
  """
  return a string that outputs the parameter in a form that NEURON can use
  """
  writeValue = value
  comment = ''
  
  if name == 'v':
    writeName = 'v(0.5)'
  elif name == 'specificCapacitance':
    writeName = 'cm'
    writeValue = 0.1 * value
    comment = ' // uF/cm^2'
  elif name == 'axialResistivity':
    writeName = 'Ra'
    writeValue = 100.0 * value
    comment = ' // ohm cm'
  elif name.endswith('Ext'):
    writeName = name.replace('Ext', 'o')
    comment = ' // mM'
  elif name.endswith('Int'):
    writeName = name.replace('Int', 'i')
    comment = ' // mM'
  else:
    firstWord = name.split('_')[0]
    if firstWord == 'm':
      writeName = name.replace('m', 'm0')
    elif firstWord == 'h':
      writeName = name.replace('h', 'h0')
    else:
      writeName = name
      if firstWord == 'gBar':
        comment = ' // uS/mm^2'
  
  if isSegmentParam:
    return '    %-19s = %19g%s' % (writeName, writeValue, comment)
  else:
    return '  %-19s   = %19g%s' % (writeName, writeValue, comment)



###############################################################################
def _writeNonSegmentParameters(fOut, startupInfo, state=False):
  """
  set the values of the parameters associated with no segments
  """
  writeParams = {}
  
  for parameter in startupInfo['simParameters']['parameters']:
    # look through all parameters to see if any match this segment
    
    if _isStateParam(parameter) != state:
      # not looking for this kind of parameter
      continue
    
    splitParam = parameter['name'].split('_')
    target = splitParam[-1]
    match = _specificity(target, startupInfo)
      
    if match > 0:
      # segment parameter, ignore it
      continue
    
    writeParams[parameter['name']] = {\
      'value' : parameter['value'], \
      'match' : match \
    }
  
  # write out all the valid parameters
  #   -for legibility, first skip the ones with _ in the name
  for name, writeParam in writeParams.items():
    if '_' in name:
      continue
    fOut.write('%s\n' % _formatParamOutput(name, writeParam['value'], False))
  #   -now write the params with _ in the name
  for name, writeParam in writeParams.items():
    if '_' not in name:
      continue
    fOut.write('%s\n' % _formatParamOutput(name, writeParam['value'], False))



###############################################################################
def _writeSegmentParameters(fOut, segment, startupInfo, state=False):
  """
  set the values of the parameters associated with this segment
  """
  writeParams = {}
  for parameter in startupInfo['simParameters']['parameters']:
    # look through all parameters to see if any match this segment
    
    if _isStateParam(parameter) != state:
      # not looking for this kind of parameter
      continue
    
    splitParam = parameter['name'].split('_')
    target = splitParam[-1]
    match = _specificity(target, startupInfo, segment)
    if match <= 0:
      # not a parameter specific to this segment
      continue
    
    writeName = '_'.join(splitParam[:-1])
    if writeName in writeParams:
      # if the parameter is already specified, go with the more specific
      # value (i.e. allow specific parameters to override general)
      if writeParams['writeName']['match'] < match:
        # new parameter is more specific, write it instead of old one
        writeParams[writeName] = {\
          'value' : parameter['value'], \
          'match' : match \
        }
    else:
      # new parameter, write it
      writeParams[writeName] = {\
        'value' : parameter['value'], \
        'match' : match \
      }
  
  # write out all the valid parameters
  fOut.write('  %s {\n' % segment['name'])
  #   -for legibility, first skip the ones with _ in the name
  for name, writeParam in writeParams.items():
    if '_' in name:
      continue
    fOut.write('%s\n' % _formatParamOutput(name, writeParam['value'], True))
  #   -now write the params with _ in the name
  for name, writeParam in writeParams.items():
    if '_' not in name:
      continue
    fOut.write('%s\n' % _formatParamOutput(name, writeParam['value'], True))
  fOut.write('  }\n')



###############################################################################
def writeModelHocFile(startupInfo, name=None):
  """
  write a .hoc file that implements a NEURON model with the specified name
  and startup information
  """
  # ensure there is only one compartment per segment
  oneCompartmentPerSegment(startupInfo)
  
  if name:
    startupInfo['modelName'] = name
  name = startupInfo['modelName']
  modelFile = os.path.join(startupInfo['startupPath'], name + '.hoc')
  startupInfo['modelHocFile'] = modelFile
  with open(modelFile, 'w') as fOut:
    fOut.write('begintemplate %s\n\n' % name)
    
    segments = startupInfo['geometry']['segments']
    for segment in segments:
      fOut.write('public %s\n' % segment['name'])
    fOut.write('\n')
    for segment in segments:
      fOut.write('create %s\n' % segment['name'])
    fOut.write('\n')
    fOut.write('proc init() {\n')
    
    fOut.write('  // Create the model segments:\n')
    for segment in segments:
      fOut.write('  create %s\n' % segment['name'])
    
    fOut.write('\n  // Set first segment as default access:\n')
    fOut.write('  access %s\n' % segments[0]['name'])
    
    fOut.write('\n  // Connect the model segments:\n')
    nodes = startupInfo['geometry']['nodes']
    for segmentInd in range(len(segments)):
      # connect each segment appropriately
      
      s1 = segments[segmentInd]
      # connect to smallest-index segment at node0 that has an index lower than
      # s1
      s1Side = 0
      nodeInd = s1['node%d' % s1Side]
      node = nodes[nodeInd]
      connections = [ind for ind in node['segments'] if ind < segmentInd]
      if connections:
        s2 = segments[min(connections)]
        s2Side = _getNodeSide(s2, nodeInd)
        fOut.write('  connect %s(%d), %s(%d)\n' % \
                     (s1['name'], s1Side, s2['name'], s2Side))
      
      # connect to smallest-index segment at node1 that has an index lower than
      # s1
      s1Side = 1
      nodeInd = s1['node%d' % s1Side]
      node = nodes[nodeInd]
      connections = [ind for ind in node['segments'] if ind < segmentInd]
      if connections:
        s2 = segments[min(connections)]
        s2Side = _getNodeSide(s2, nodeInd)
        fOut.write('  connect %s(%d), %s(%d)\n' % \
                     (s1['name'], s1Side, s2['name'], s2Side))
    
    fOut.write('\n  // Set the physical dimensions of the model segments:\n')
    for segment in segments:
      diameter = segment['surfaceArea'] / segment['length'] / math.pi
      fOut.write('  %s {\n' % segment['name'])
      fOut.write('    diam = %19g // um\n' % diameter)
      fOut.write('    L    = %19g // um\n' % segment['length'])
      fOut.write('    nseg = %d\n' % segment['numCompartments'])
      fOut.write('  }\n')
    
    fOut.write('\n  // Add channels to model segments:\n')
    for segment in segments:
      # add appropriately tagged channels to each compartment
      addChannels = [chan for chan in startupInfo['channels'] \
                     if chan['tag'] == '*' or \
                        chan['tag'] in segment['tags'] or \
                        chan['tag'] in segment['compartmentNames'][0]]
      if addChannels:
        fOut.write('  %s {\n' % segment['name'])
        for channel in addChannels:
          fOut.write('    insert %s\n' % channel['name'])
        fOut.write('  }\n')
    
    fOut.write('\n  // Set the value of non-state parameters:\n')
    _writeNonSegmentParameters(fOut, startupInfo, state=False)
    for segment in segments:
      _writeSegmentParameters(fOut, segment, startupInfo, state=False)
    
    fOut.write('}\n')
    fOut.write('\n')
    fOut.write('proc setState() {\n')
    fOut.write('  // Initialize the model:\n')
    fOut.write('  finitialize()\n')
    fOut.write('  fcurrent()\n')
    fOut.write('  // Set the values of state parameters:\n')
    _writeNonSegmentParameters(fOut, startupInfo, state=True)
    for segment in segments:
      _writeSegmentParameters(fOut, segment, startupInfo, state=True)
    fOut.write('}\n')
    fOut.write('endtemplate %s\n' % name)


###############################################################################
def _parseArguments():
  arguments = sys.argv
  
  if len(arguments) not in [3, 4]:
    print(_usageStr)
    raise TypeError('Incorrect number of arguments.')
  
  modelName = arguments[1]
  startFile = arguments[2]
  if len(arguments) == 4:
    paramsFile = arguments[3]
  else:
    paramsFile = None
  return (modelName, startFile, paramsFile)



###############################################################################
if __name__ == "__main__":
  (modelName, startupFile, parametersFile) = _parseArguments()

  startupInfo = \
    neuron_getStartupInfo.getStartupInfo(startupFile, parametersFile)
  
  writeModelHocFile(startupInfo, modelName)
  
  sys.exit(0)
