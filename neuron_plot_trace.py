#!/usr/bin/python
# -*- coding: utf-8 -*-



_usageStr=\
"""usage: neuron_plot_trace.py traceFile [traceFile2] [traceFile3] ...
         loads and plots the traces in specified trace files
     Can pass the -monitor keyword to monitor tracefiles for updates and replot
       if necessary, but it's broken currently because of the .show()/.draw()
       mechanism in pyplot
"""



import sys, os
import matplotlib.pyplot as pyplot
import matplotlib
from plotXY import *
from time import sleep


# Make output fonts compatible with Illustrator
matplotlib.rcParams['pdf.fonttype'] = 42


_lineNum = 0



###############################################################################
def _getNextLine(fIn):
  """
  get the next line that isn't empty after removing comments, and return the
  non-comment part of that line
  """
  global _lineNum
  nextLine = ''
  while(len(nextLine) == 0):
    # while the cleaned line is empty, iterate
    nextLine = fIn.readline()        # get the next line
    _lineNum = _lineNum + 1            # increment lineNum
    commentInd = nextLine.find('#')  # get the index to the first comment mark
    if commentInd > -1:
      # there's a comment, remove it, and then strip white space
      nextLine = nextLine[:commentInd].strip()
    else:
      # no comment, strip white space
      nextLine = nextLine.strip()
    
  return nextLine



###############################################################################
def loadTraces(traceFile, monitor=False):
  """
  load all the traces in traceFile into a dictionary object
  """
  global _lineNum
  _lineNum = 0
  traces = []
  try:
    with open(traceFile, 'r') as fIn:
      if monitor:
        mTime = os.path.getmtime(traceFile)
      else:
        mTime = None
      
      # first get the number of traces
      line = _getNextLine(fIn)
      numTraces = int(line)
      
      # read in the header info for each trace
      for n in range(numTraces):
        _readTraceHeader(fIn, traces)
      
      # read in the data for each trace
      for trace in traces:
        # first just add a few extra fields to trace
        trace['fileName'] = traceFile
        trace['uniqueName'] = trace['name'] + '_' + traceFile
        if monitor:
          trace['mTime'] = mTime
        # read in data
        _readTraceData(fIn, trace)
  
  except StandardError as err:
    sys.tracebacklimit = 0
    raise IOError('Error reading %s line %d: %s' % \
                  (traceFile, _lineNum, err.message))

  return traces



###############################################################################
def _readTraceHeader(fIn, traces):
  """
  read a header line from the file and add a new trace to traces and traceNames
  """
  # get the next header line
  headerLine = _getNextLine(fIn)
  # split it into its four component parts (will work even if traceName has
  # white space)
  (traceName, units, numT, dT) = headerLine.rsplit(None, 3)
  # add to traces
  traces.append( {'name'  : traceName, \
                  'units' : units, \
                  'numT'  : int(numT), \
                  'dT'    : float(dT), \
                  'data'  : [] } )
  


###############################################################################
def _readTraceData(fIn, trace):
  """
  read the data corresponding to trace from fIn
  """
  trace['data'] = \
    [float(_getNextLine(fIn)) for n in range(trace['numT'])]



###############################################################################
def saveTraces(traces, traceFile):
  """
  save all the traces a dictionary object to traceFile
  """
  with open(traceFile, 'w') as fOut:
    # write the number of traces
    fOut.write('# number of  traces\n')
    fOut.write('%d\n' % len(traces))
    
    # write the header information
    fOut.write('# name units numT dt\n')
    for traceName in traces:
      trace = traces[traceName]
      fOut.write('%s %s %d %g\n' % \
                 (traceName, trace['units'], trace['numT'], trace['dT']))
    
    # write the trace data
    for traceName in traces:
      fOut.write('#%s\n' % traceName)
      for val in traces[traceName]['data']:
        fOut.write('%g\n' % val)



###############################################################################
def plotTrace(trace, dupTraces=None, figures=None,
              labelSize=30, titleSize=30, tickSize=24):
  """
  plot the trace in a new figure
  """
  (dT, tUnits) = scaleTraceTime(trace, 'ms')
  tFactor = dT / trace['dT']
  units = trace['units']
  
  # do any conversions to dT, tUnits based on tUnits and numT?
  t = [dT * n for n in range(trace['numT'])]
  
  xLabel = 'Time (%s)' % tUnits
  yLabel = '%s (%s)' % (trace['name'], units)

  if dupTraces:
    # make shallow copy of figures
    
    # first make overlay plot
    legendName = 'fileName' # or 'uniqueName'
    if figures is None:
      overlayFig = pyplot.figure()
      diffFig = pyplot.figure()
      figures = [overlayFig, diffFig]
    else:
      overlayFig, diffFig = figures[:]
      overlayFig.clf()
      diffFig.clf()
    titleStr = trace['name'] + ' overlaid'
    for dupNum in range(len(dupTraces)):
      trace2 = dupTraces[dupNum]
      dT2 = trace2['dT'] * tFactor
      units2 = trace2['units']
      t2 = [dT2 * n for n in range(trace2['numT'])]
      plotXY(t2, trace2['data'], '-', color=getColor(dupNum+2), \
             xLabel=xLabel, yLabel=yLabel, title=titleStr, \
             legendLabel=trace2[legendName], figure=overlayFig, linewidth=2)
    
    titleStr = trace['name'] + ' overlaid'
    plotXY(t, trace['data'], '-', color=getColor(1), \
           xLabel=xLabel, yLabel=yLabel, title=titleStr, \
           legendLabel=trace[legendName], figure=overlayFig)
    pyplot.legend(loc=0)
    
    # make difference plots
    numDiff = 0
    titleStr = trace['name'] + ' difference'
    for dupNum in range(len(dupTraces)):
      trace2 = dupTraces[dupNum]
      numDiff += 1
      traceDiff = [y2 - y for (y, y2) in zip(trace['data'], trace2['data'])]
      numT = min(trace['numT'], trace2['numT'])
      plotXY(t[:numT], traceDiff, '-', color=getColor(dupNum + 2), \
             xLabel=xLabel, yLabel=yLabel, title=titleStr, \
             legendLabel=trace2[legendName], figure=diffFig)
    if numDiff > 0:
      pyplot.legend(loc=0)
  else:
    if figures is None:
      traceFig = pyplot.figure()
      figures = [traceFig]
    else:
      traceFig = figures[0]
      traceFig.clf()
    plotXY(t, trace['data'], 'k-',
           xLabel=xLabel, yLabel=yLabel, title=trace['name'], figure=traceFig)
  
  return figures


###############################################################################
def scaleTraceTime(originalTrace, originalUnits):
  """
  return dT and tUnits in a convenient unit
  """
  dT = originalTrace['dT']
  numT = originalTrace['numT']
  tFinal = dT * (numT - 1)
  
  upConvert = \
    { \
      'ns' : {'unit': 'us', 'factor' : 1000}, \
      'μs' : {'unit': 'ms', 'factor' : 1000}, \
      'us' : {'unit': 'ms', 'factor' : 1000}, \
      'ms' : {'unit': 's',  'factor' : 1000}, \
      's'  : {'unit': 'm',  'factor' : 60},\
      'm'  : {'unit': 'h',  'factor' : 60},\
      'h'  : {'unit': 'd',  'factor' : 24}\
    }
  downConvert = \
    { \
      'us' : {'unit': 'ns', 'factor' : 1000}, \
      'μs' : {'unit': 'ns', 'factor' : 1000}, \
      'ms' : {'unit': 'us', 'factor' : 1000}, \
      's'  : {'unit': 'ms', 'factor' : 1000}, \
      'm'  : {'unit': 's',  'factor' : 60},\
      'h'  : {'unit': 'm',  'factor' : 60},\
      'd'  : {'unit': 'h',  'factor' : 24}\
    }
  
  tUnits = originalUnits
  if tFinal >= 1:
    while tUnits in upConvert:
      # upconvert as long as the result leaves tFinal >= 1
      factor = upConvert[tUnits]['factor']
      tFinal = tFinal / factor
      if tFinal >= 1:
        dT = dT / factor
        tUnits = upConvert[tUnits]['unit']
      else:
        break
  else:
    while tUnits in downConvert and tFinal < 1:
      # downconvert as long as tFinal < 1
      factor = downConvert[tUnits]['factor']
      tFinal = tFinal * factor
      dT = dT * factor
      tUnits = downConvert[tUnits]['unit']
  return (dT, tUnits) 



###############################################################################
def getColor(colorNum):
  colors = [ \
    (0,   0,   0  ), \
    (0,   0,   255), \
    (255, 0,   0  ), \
    (0,   255, 0  ), \
    (255, 0,   182), \
    (0,   83,  0  ), \
    (255, 211, 0  ), \
    (0,   159, 255), \
    (154, 77,  66 ), \
    (0,   255, 190), \
    (120, 63,  193), \
    (31,  150, 152), \
    (255, 172, 253), \
    (177, 204, 113), \
    (241, 8,   92 ), \
    (254, 143, 66 ), \
    (221, 0,   255), \
    (32,  26,  1  ), \
    (114, 0,   85 ), \
    (118, 108, 149), \
    (2,   173, 36 ), \
    (200, 255, 0  ), \
    (136, 108, 0  ), \
    (255, 183, 159), \
    (133, 133, 103), \
    (161, 3,   0  ), \
    (20,  249, 255), \
    (0,   71,  158), \
    (220, 94,  147), \
    (147, 212, 255), \
    (0,   76,  255) \
  ]
  # get desired color and scale it to float in interval [0, 1]
  return tuple([ c / 255.0 for c in colors[colorNum] ])



###############################################################################
def findDuplicateTraces(traces, updateList):
  if updateList is None:
    updateList = []
  
  def _isDup(t1, t2):
    if t1['name'] == t2['name'] or \
       t1['name'] + '_0' == t2['name'] or \
       t1['name'] == t2['name'] + '_0':
      return True
    else:
      return False
  
  duplicates = []
  noDupTraces = []
  updates = []
  while traces:
    trace = traces.pop(0)
    update = trace in updateList
    dups = [t for t in traces if _isDup(t, trace)]
    for t in dups:
      traces.remove(t)
      if t in updateList:
        update = True
    noDupTraces.append(trace)
    duplicates.append(dups)
    updates.append(update)
  
  return noDupTraces, duplicates, updates



###############################################################################
def plotTraces(traces, monitor=False, updateList=None, figures=None):
  traces, duplicates, updates = findDuplicateTraces(traces[:], updateList)
  
  if figures is None:
    if monitor:
      pyplot.ion()
    figures = { trace['uniqueName'] : plotTrace(trace, dups)
                for trace, dups in zip(traces, duplicates) }
    
    # Show figures. If not monitoring, wait until all figures are closed
    #pyplot.show(block = not monitor)
    if monitor:
      for fName, figList in figures.items():
        for fig in figList:
          fig.canvas.draw()
      pyplot.draw()
    else:
      pyplot.show()
  else:
    for trace, dups, needPlot in zip(traces, duplicates, updates):
      if needPlot:
        print('Need Plot!')
        plotTrace(trace, dups, figures[trace['uniqueName']])
    
    # Update figures
    print('Update!')
    for fName, figList in figures.items():
      for fig in figList:
        print('draw')
        fig.canvas.draw()
    pyplot.draw()
  
  return figures



###############################################################################
def monitorTraces(tracesFiles, traces, figures, sleepTime=1):
  dependTraces = { traceFile : [trace for trace in traces
                               if trace['fileName'] == traceFile]
                   for traceFile in traceFiles }
  mTimes = { traceFile : dependTraces[traceFile][0]['mTime']
             for traceFile in traceFiles }
  
  while True:
    updateList = []
    sleep(sleepTime)
    for traceFile, mTime in mTimes.items():
      currentMTime = os.path.getmtime(traceFile)
      if currentMTime > mTime:
        needUpdate = True
        updateList.extend(dependTraces[traceFile])
        mTimes[traceFile] = currentMTime
    if updateList:
      plotTraces(traces, monitor=True, updateList=updateList, figures=figures)
    else:
      for fName, figList in figures.items():
        for fig in figList:
          print('draw')
          fig.canvas.draw()



###############################################################################
def _parseArguments():
  arguments = sys.argv[1:]
  if len(arguments) < 1:
    print(_usageStr)
    sys.tracebacklimit = 1
    raise TypeError('Incorrect number of arguments.')

  monitor=False
  traceFiles = []
  for arg in arguments[:]:
    if arg.startswith('-'):
      a = arg.lstrip('-')
      if a == 'monitor' or a == 'm':
        monitor=True
      else:
        raise ValueError('Unknown special argument: %s' % arg)
    else:
      traceFiles.append(arg)
  
  return traceFiles, monitor


  
###############################################################################
if __name__ == "__main__":
  traceFiles, monitor = _parseArguments()
  
  # load all the traces
  traces = []
  for traceFile in traceFiles:
    traces.extend( loadTraces(traceFile, monitor) )
  
  figs = plotTraces(traces, monitor)
  
  if monitor:
    monitorTraces(traceFiles, traces, figs)

  sys.exit(0)
