#!/usr/bin/python



_usageStr=\
"""usage: neuron_getStartupInfo.py startupFile [overrideParametersFile]
     get the startup information for a neuron simulation by reading the startup
     file, associated geometry file, and if specified an overriding parameters
     file
"""



import os, sys, math



###############################################################################
def readStartupFile(startupFileName):
  """
  get dictionary object describing neuron model startup info by reading file
  """
  startupInfo = { \
    'startupFileName' : startupFileName, \
    'startupPath' : os.path.dirname(os.path.abspath(startupFileName)), \
    'geometryFile' : '', \
    'channelDir' : '', \
    'time' : float('inf'), \
    'traces' : [], \
    'channels' : [], \
    'parameters' : [] \
  }
  
  openTags = {'channel' : False, 'parameter' : False}
  
  lineNum = 0
  with open(startupFileName, 'r') as fIn:
    try:
      for line in fIn:
        # loop through each line in the file
        
        # inc the line number
        lineNum = lineNum + 1
        
        # parse the line in startup file, adding info to startupInfo
        _parseStartLine(line, startupInfo, openTags)
        
        # check the number of open tags
        openList = [tag for tag in openTags if openTags[tag]]
        if len(openList) > 1:
          RuntimeError("Multiple tags open (" + ' '.join(openList) + ")")

      # check the number of open tags
      openList = [tag for tag in openTags if openTags[tag]]
      if len(openList) > 0:
        RuntimeError("Tags open at end of file (" + ' '.join(openList) + ")")
  
    except StandardError as err:
      sys.tracebacklimit = 0
      raise IOError('Error reading %s line %d: %s' % \
                    (startupFileName, lineNum, err.message))
  
  return startupInfo



###############################################################################
def readGeometryFile(geometryFileName):
  """
  get dictionary object describing neuron model geometry info by reading file
  """
  geometryInfo = { \
    'geometryFileName' : geometryFileName, \
    'geometryPath'     : os.path.dirname(os.path.abspath(geometryFileName)), \
    'nodes'            : [], \
    'segments'         : [], \
    'tags'             : {'*' : 0}, \
    'numCompartments'  : 0, \
    'surfaceArea'      : 0.0, \
    'volume'           : 0.0 \
  }
  
  openTags = set([])
  
  lineNum = 0
  with open(geometryFileName, 'r') as fIn:
    # read the geometry file
    try:
      for line in fIn:
        # loop through each line in the file
        
        # inc the line number
        lineNum = lineNum + 1
        # parse the line in geometry file, adding info to geometryInfo
        _parseGeometryLine(line, geometryInfo, openTags)

      # check the number of open tags
      if openTags:
        RuntimeError("Tags open at end of file (" + ' '.join(openList) + ")")
  
    except StandardError as err:
      sys.tracebacklimit = 0
      raise IOError('Error reading %s line %d: %s' % \
                    (geometryFileName, lineNum, err.message))
  
  # make sure that there are appropriate nodes defined
  _addConnectingNodes(geometryInfo)
  
  # try to establish names for the segments based on tags, but fall back and
  # name them by segment number if necessary
  for segment in geometryInfo['segments']:
    uniqueTags = {tag for tag in segment['tags']}
    for s2 in geometryInfo['segments']:
      if s2 == segment:
        continue
      uniqueTags -= s2['tags']
    if uniqueTags:
      segment['name'] = uniqueTags.pop()
    else:
      segment['name'] = 'Segment%d' % geometryInfo['segments'].index(segment)
  
  return geometryInfo



###############################################################################
def readParametersFile(parametersFile):
  """
  get neuron model parameters by reading file
  """
  parameters = {'value' : float('NaN'), 'parameters' : []}
  
  lineNum = 0
  with open(parametersFile, 'r') as fIn:
    try:
      for line in fIn:
        # loop through each line in the file
        
        # inc the line number
        lineNum = lineNum + 1
        
        # parse the line in parameters file
        #   -remove comments and endline
        line = line.split('#', 1)[0].strip('\n')
        
        #   -split line into words separated by white space      
        splitLine = line.split(None)
        
        if len(splitLine) == 0:
          # skip blank lines or comment-only lines
          continue
        
        if len(splitLine) != 2:
          # only constant parameters should exist in this file
          raise IOError("Line doesn't describe a constant parameter")
        
        name = splitLine[0]
        value = float(splitLine[1])
        if name == "value":
          parameters['value'] = value
        else:
          parameters['parameters'].append( \
            {'name' : name, 'value' : value, 'isConstant' : True} )
  
    except StandardError as err:
      sys.tracebacklimit = 0
      raise IOError('Error reading %s line %d: %s' % \
                    (parametersFileName, lineNum, err.message))
  
  return parameters  



###############################################################################
def _addConnectingNodes(geometry):
  """
  make sure that there are appropriate nodes defined
  """
  # first get the maximum node referred to by the segments
  maxNode = -1
  for segment in geometry['segments']:
    maxNode = max(maxNode, segment['node0'], segment['node1'])
  if len(geometry['nodes']) not in [0, maxNode + 1]:
    raise RuntimeError('Geometry specifies an incorrect number of nodes')
  
  if not geometry['nodes']:
    # nodes are empty, create some blank ones
    for n in range(maxNode + 1):
      blankNode = { \
        'x'             : float('NaN'), \
        'y'             : float('NaN'), \
        'z'             : float('NaN'), \
        'segments'      : [], \
        'compartments'  : [] \
      }
      geometry['nodes'].append(blankNode)
  
  # record all the segments and compartments that connect to this node
  for ind in range(len(geometry['segments'])):
    segment = geometry['segments'][ind]
    node0 = geometry['nodes'][segment['node0']]
    node1 = geometry['nodes'][segment['node1']]
    
    node0['segments'].append(ind)
    node0['compartments'].append(segment['compartmentNums'][0])
    
    node1['segments'].append(ind)
    node1['compartments'].append(segment['compartmentNums'][-1])



###############################################################################
#                               parse functions:                              #
###############################################################################



def _setGeometry(splitLine, startupInfo, openTags):
  if len(splitLine) != 2:
    RuntimeError("Incorrect number of words using \"geometry\" keyword")
  startupInfo['geometryFile'] = splitLine[1]

def _setChannelDir(splitLine, startupInfo, openTags):
  if len(splitLine) != 2:
    RuntimeError("Incorrect number of words using \"channeldir\" keyword")
  startupInfo['channelDir'] = splitLine[1]

def _setTime(splitLine, startupInfo, openTags):
  if len(splitLine) != 2:
    RuntimeError("Incorrect number of words using \"time\" keyword")
  startupInfo['time'] = float(splitLine[1])

def _addRecordTrace(splitLine, startupInfo, openTags):
  if len(splitLine) != 4:
    RuntimeError("Incorrect number of words using \"record\" keyword")
  trace = { \
    'type' : 'record', \
    'target' : splitLine[1], \
    'dT' : float(splitLine[2]), \
    'fileName' : '', \
    'traceNumber' : -1, \
    'fitTau' : float('NaN') \
  }
  startupInfo['traces'].append(trace)

def _addClampTrace(splitLine, startupInfo, openTags):
  if len(splitLine) != 5:
    RuntimeError("Incorrect number of words using \"clamp\" keyword")
  trace = { \
    'type' : 'clamp', \
    'target' : splitLine[1], \
    'dT' : float('NaN'), \
    'fileName' : splitLine[2], \
    'traceNumber' : int(splitLine[3]), \
    'fitTau' : float('NaN') \
  }
  startupInfo['traces'].append(trace)

def _addFitTrace(splitLine, startupInfo, openTags):
  if len(splitLine) != 5:
    RuntimeError("Incorrect number of words using \"fit\" keyword")
  trace = { \
    'type' : 'fit', \
    'target' : splitLine[1], \
    'dT' : float('NaN'), \
    'fileName' : splitLine[2], \
    'traceNumber' : int(splitLine[3]), \
    'fitTau' : float(splitLine[4]) \
  }
  startupInfo['traces'].append(trace)

def _addChannel(splitLine, startupInfo, openTags):
  if len(splitLine) not in [2, 3]:
    RuntimeError("Incorrect number of words using \"channel\" keyword")
  if len(splitLine) == 2 and splitLine[1] == "</channel>":
    if openTags['channel']:
      openTags['channel'] = False
    else:
      RuntimeError("Tried to close channel tag but it wasn't open")
  elif len(splitLine) == 3:
    channel = {'name': splitLine[1], 'tag': splitLine[2]}
    startupInfo['channels'].append(channel)
  else:
    RuntimeError("Improper use of \"channel\" keyword")

def _addParameter(splitLine, startupInfo, openTags):
  if len(splitLine) not in [2, 3, 4, 6]:
    RuntimeError("Incorrect number of words using \"parameter\" keyword")
  if len(splitLine) == 2:
    # perhaps closing the parameter tag
    if splitLine[1] == "</parameter>":
      if openTags['parameter']:
        openTags['parameter'] = False
      else:
        RuntimeError("Tried to close parameter tag but it wasn't open")
    else:
      RuntimeError("Improper use of \"parameter\" keyword")
  else:
    # adding a parameter
    minVal = float(splitLine[2])
    if len(splitLine) == 3:
      maxVal = minVal
      startMin = minVal
      startMax = maxVal
      paramType = 'constant'
      isConstant = True
    elif len(splitLine) == 4:
      maxVal = float(splitLine[3])
      startMin = minVal
      startMax = maxVal
      if minVal > maxVal:
        RuntimeError('Invalid parameter range')
      elif minVal == maxVal:
        paramType == 'constant'
        isConstant = True
      else:
        isConstant = False
        if minVal * maxVal > 0:
          paramType = 'logDistributed'
        else:
          paramType = 'uniform'
    else:
      maxVal = float(splitLine[3])
      startMin = float(splitLine[4])
      startMax = float(splitLine[5])
      if minVal > startMin or startMin > startMax or startMax > maxVal:
        RuntimeError('Invalid parameter range')
      elif minVal == maxVal:
        paramType == 'constant'
        isConstant = True
      else:
        isConstant = False
        if minVal * maxVal > 0:
          paramType = 'logDistributed'
        else:
          paramType = 'uniform'
    
    if isConstant:
      value = minVal
    else:
      value = float('NaN')
    
    parameter = { 'name': splitLine[1], 'minVal' : minVal, 'maxVal' : maxVal, \
                  'startMin' : startMin, 'startMax' : startMax, \
                  'isConstant' : isConstant, 'paramType' : paramType, \
                  'value' : value }
    
    
    startupInfo['parameters'].append(parameter)



###############################################################################
def _parseStartLine(line, startupInfo, openTags):
  # parse the line in startup file, adding info to startupInfo

  # remove comments and endline
  line = line.split('#', 1)[0].strip('\n')
  
  # split line into words separated by white space      
  splitLine = line.split(None)
  
  if len(splitLine) == 0:
    # skip blank lines or comment-only lines
    return
  
  # handle any open tags (basically add in keyword)
  for tag in openTags:
    if openTags[tag]:
      splitLine.insert(0, tag)
  
  # the first word in a line is the keyword
  keyword = splitLine[0].lower()
  
  parseDict = { \
    "geometry"   : _setGeometry, \
    "channeldir" : _setChannelDir, \
    "time"       : _setTime, \
    "record"     : _addRecordTrace, \
    "clamp"      : _addClampTrace, \
    "fit"        : _addFitTrace, \
    "channel"    : _addChannel, \
    "parameter"  : _addParameter \
  }
  
  if keyword in parseDict:
    # handle keyword from parseDict by calling the appropriate function
    parseDict[keyword](splitLine, startupInfo, openTags)
  elif keyword.startswith('<') and keyword.endswith('>'):
    # maybe a tag is being opened
    tagKeyword = keyword[1:-1]
    if tagKeyword in openTags:
      # open the appropriate tag
      openTags[tagKeyword] = True
    else:
      RuntimeError("Unknown tag \"" + keyword + "\"")
  else:
    RuntimeError("Unknown keyword \"" + keyword + "\"")



###############################################################################
def _handleGeoTags(splitLine, geometryInfo, openTags):
  numTags = 0
  for word in splitLine:
    if word.startswith('<') and word.endswith('>'):
      # this line defines a tag
      numTags = numTags + 1
      if len(word) < 3 or (word[1] == '/' and len(word) < 4):
        RuntimeError('Invalid tag' + word)
      if word[1] == '/':
        # this word is closing a tag
        tag = word[2:-1]
        if tag not in openTags:
          RuntimeError("Tried to close tag \"%s\" but it wasn't open" % tag)
        openTags.remove(tag)
      else:
        # this word is opening a tag
        tag = word[1:-1]
        if tag in openTags:
          RuntimeError("Tried to open tag \"%s\" but it was already open" %tag)
        openTags.add(tag)
        if tag not in geometryInfo['tags']:
          # add tag to list of all tags, note that it is currently unused
          geometryInfo['tags'][tag] = 0
  
  if numTags > 0:
    if numTags != len(splitLine):
      RuntimeError('Tags and non-tag entries on the same line')
    # clear splitLine, it's already been dealt with
    splitLine = []



###############################################################################
def _addNode(splitLine, geometryInfo, openTags):
  node = { \
    'x'             : float(splitLine[0]), \
    'y'             : float(splitLine[1]), \
    'z'             : float(splitLine[2]), \
    'segments'      : [], \
    'compartments'  : [] \
  }
  geometryInfo['nodes'].append(node)



###############################################################################
def _addCircularSegment(splitLine, geometryInfo, openTags):
  length =float(splitLine[3])
  radius = float(splitLine[4])
  perimeter = 2 * math.pi * radius
  surfaceArea = 1.0e-6 * perimeter * length           # mm^2
  crossSectionArea = math.pi * radius * radius        # um^2
  volume = 1.0e-9 * crossSectionArea * length         # mm^3
  
  segment = { \
    'node0'            : int(splitLine[0]), \
    'node1'            : int(splitLine[1]), \
    'numCompartments'  : int(splitLine[2]), \
    'length'           : length, \
    'semiMajor'        : radius, \
    'semiMinor'        : radius, \
    'elipseAngle'      : 0.0, \
    'crossSectionArea' : crossSectionArea, \
    'surfaceArea'      : surfaceArea, \
    'volume'           : volume, \
    'tags'             : {tag for tag in openTags}, \
    'compartmentNums'  : [], \
    'compartmentNames' : [] \
  }
  
  _setCompartmentNames(segment, geometryInfo)
  
  geometryInfo['segments'].append(segment)
  geometryInfo['surfaceArea'] += segment['surfaceArea']
  geometryInfo['volume'] += segment['volume']
  geometryInfo['numCompartments'] += segment['numCompartments']



###############################################################################
def _addElipticalSegment(splitLine, geometryInfo, openTags):
  length =float(splitLine[3])
  semiMajor = float(splitLine[4])
  semiMinor = float(splitLine[5])
  # Approximate formula for perimeter of elipse, by David Cantrell
  # (Accurate to within 0.02%)
  s = 0.825056 # optimal power for arbitrary elipse eccentricity
  perimeter = 4 * (semiMajor + semiMinor) - \
              2 * (4 - math.pi) * semiMajor * semiMinor * \
                (0.5 * (semiMajor**s + semiMinor**s))**(-1.0/s)
  surfaceArea = 1.0e-6 * perimeter * length           # mm^2
  crossSectionArea = math.pi * semiMajor * semiMinor  # um^2
  volume = 1.0e-9 * crossSectionArea * length         # mm^3
  
  segment = { \
    'node0'            : int(splitLine[0]), \
    'node1'            : int(splitLine[1]), \
    'numCompartments'  : int(splitLine[2]), \
    'length'           : length, \
    'semiMajor'        : semiMajor, \
    'semiMinor'        : semiMinor, \
    'elipseAngle'      : float(splitLine[6]), \
    'crossSectionArea' : crossSectionArea, \
    'surfaceArea'      : surfaceArea, \
    'volume'           : volume, \
    'tags'             : {tag for tag in openTags}, \
    'compartmentNums'  : [], \
    'compartmentNames' : [] \
  }
  
  _setCompartmentNames(segment, geometryInfo)
  
  geometryInfo['segments'].append(segment)
  geometryInfo['surfaceArea'] += segment['surfaceArea']
  geometryInfo['volume'] += segment['volume']
  geometryInfo['numCompartments'] += segment['numCompartments']



###############################################################################
def _setCompartmentNames(segment, geometryInfo):
  """
  set the names of compartments in the segment, and update the number of
  compartments with each tag
  """
  numNames = 1 + len(segment['tags'])
  for compNum in range(segment['numCompartments']):
    # find all the valid ways to refer to this compartment
    #   -first, the basic name is just the compartment number (as a string)
    geoTags = geometryInfo['tags']
    compartmentNum = geoTags['*']
    compartmentNames = [str(geoTags['*'])]
    geoTags['*'] += 1
    #   -next add a name for each open tag
    for name in segment['tags']:
      compartmentNames.append('%s%d' % (name, geoTags[name]))
      geoTags[name] += 1
    
    # append the compartment number to the segment compartment nums
    segment['compartmentNums'].append(compartmentNum)
    # append this list of names to the segment names
    segment['compartmentNames'].append(compartmentNames)
  


###############################################################################
def _parseGeometryLine(line, geometryInfo, openTags):
  """
  parse the line in startup file, adding info to geometryInfo
  """

  # remove comments and endline
  line = line.split('#', 1)[0].strip('\n')
  
  # split line into words separated by white space      
  splitLine = line.split(None)
  
  # open or close tags as requested
  _handleGeoTags(splitLine, geometryInfo, openTags)
  
  if len(splitLine) == 0:
    # skip blank lines or comment-only lines
    return
  
  # the number of entries on the line is the keyword
  keyword = len(splitLine)
  
  parseDict = { \
    3   : _addNode, \
    5   : _addCircularSegment, \
    7   : _addElipticalSegment \
  }
  
  if keyword in parseDict:
    # handle keyword from parseDict by calling the appropriate function
    parseDict[keyword](splitLine, geometryInfo, openTags)
  else:
    RuntimeError("Syntax error")



###############################################################################
def getStartupInfo(startupFile, parametersFile = None):
  """
  get the startup information for a neuron simulation by reading the startup
  file, associated geometry file, and if specified an overriding parameters
  file
  """
  startupInfo = readStartupFile(startupFile)
  startupInfo["geometry"] = readGeometryFile(startupInfo["geometryFile"])
  if parametersFile:
    startupInfo["simParameters"] = readParametersFile(parametersFile)
  else:
    startupInfo["simParameters"] = \
      {'value' : float('NaN'), 'parameters' : startupInfo["parameters"]}
  return startupInfo



###############################################################################
def _parseArguments():
  arguments = sys.argv
  
  if len(arguments) not in [2, 3]:
    print(_usageStr)
    raise TypeError('Incorrect number of arguments.')
  
  startFile = arguments[1]
  if len(arguments) == 3:
    paramsFile = arguments[2]
  else:
    paramsFile = None
  return (startFile, paramsFile)



###############################################################################
if __name__ == "__main__":
  (startupFile, parametersFile) = _parseArguments()

  startupInfo = getStartupInfo(startupFile, parametersFile)
  
  from pprint import pprint
  pprint(startupInfo)
  
  sys.exit(0)

