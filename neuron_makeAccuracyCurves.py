#!/usr/bin/python


_usageStr=\
"""usage: neuron_makeAccuracyCurves.py [startupFileName]
         Simulates a neuron model in NEURON and simulate_neuron.bin with
         varying tolerances, to determine the time/accuracy trade-off. Then
         saves the traces and plots the result. If traces already exist prior
         to running the script, they are loaded instead of re-simulated.
"""



import sys, os, time
import json
import matplotlib.pyplot as pyplot
import matplotlib
import neuron_plot_trace
import numpy
#import subprocess

_maxRunMinutes = 5.25    # how long it takes NEURON at maximum accuracy
#_maxRunMinutes = 15.0    # really long time
_AlwaysPlotExistingTrace = True


# update font properties for illustrator compatibility
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rc('font', **{'sans-serif' : 'Arial', 'family' : 'sans-serif'})


###############################################################################
def getNeuronTraceFile(startupFile, fileNames):
  dataFile = fileNames['dataFile']
  splitData = os.path.split(dataFile)
  return os.path.join(splitData[0], 'Sim' + splitData[1])



###############################################################################
def simulateInNeuron(baseDir, tol):
  """
  simulate a model in neuron at the requested accuracy
  """

  # point to the startup file
  startupFile = os.path.join(baseDir, 'start_neuron.txt')
  # get info about other files associated with the simulation
  fileNames = neuron_createModelHocFile.getFileNames(startupFile)
  # get the name of the file containing the output traces
  traceFile = getNeuronTraceFile(startupFile, fileNames)
  
  # run the simulation
  (sectionList, modelName) = \
                neuron_createModelHocFile.createModelHocFile(startupFile)
  runTime = neuron_simulate.simulateNeuron(startupFile, sectionList, \
                                           modelName, tol=tol)

  # load the output traces
  neuronTraces = neuron_plot_trace.loadTraces(traceFile)
  # return the voltage trace
  for trace in neuronTraces:
    if trace['units'] == 'mV':
      trace['tol'] = tol
      trace['runTime'] = runTime
      os.remove(traceFile)
      return trace
  
  raise RuntimeError('No voltage trace produced by NEURON')



###############################################################################
def getNeuronCurveTraces(baseDir):
  """
  get traces produced by simulating in NEURON, either load in old traces or
  if they're nonexistant, simulate new ones
  """

  outFile = os.path.join(baseDir, 'neuroncurve.json')
  try:
    trace_mtime = os.stat(outFile).st_mtime
    if _AlwaysPlotExistingTrace:
      trace_mtime = float('inf')
  except:
    trace_mtime = float('-inf')
    
  startupFile = os.path.join(baseDir, 'start_neuron.txt')
  startup_mtime = os.stat(startupFile).st_mtime  
  
  if startup_mtime > trace_mtime:
    import neuron_writeModelHocFile
    import neuron_simulate
    
    traces = []

    exponent = -2;
    frontList = [1];
    while True:
      # get the next tol
      if not frontList:
        frontList = [1, 2, 5]
        exponent = exponent - 1
        if exponent < -15:
          break

      tol = float('%de%d' % (frontList.pop(), exponent))

      try:
        newTrace = simulateInNeuron(baseDir, tol)
      except RuntimeError:
        break
      traces.append(newTrace)
    
    with open(outFile, 'w') as fOut:
      json.dump(traces, fOut)
  else:
    with open(outFile, 'r') as fIn:
      traces = json.load(fIn)
  
  return traces
  


###############################################################################
def simulateInCpp(baseDir, tol):
  # point to the startup file and the output trace file
  program = 'simulate_neuron.bin'
  programFile = os.path.abspath(os.path.join(baseDir, program))
  startupFile = os.path.join(baseDir, 'startup.txt')
  traceFile = os.path.join(baseDir, 'recorded_traces.txt')
  
  
  # run the simulation
  startTime = time.time()
  systemCommand = '%s -startup %s -outfile %s -accuracy %s -verbosity 0' % \
                  (programFile, startupFile, traceFile, tol) 
  returnStatus = os.system(systemCommand)
  #p = subprocess.Popen([systemCommand], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  #returnStatus = p.wait()
  #output = p.stdout.read()
  #if len(output) > 1:
  #  print(output[:-1])
  
  if returnStatus != 0:
    #print(p.stderr.read())
    raise RuntimeError('%s failed' % program)
  runTime = time.time() - startTime
  
  # display progress
  print('%s: tol = %g, time = %g' % (program, tol, runTime))
  
  # load the output traces
  cppTraces = neuron_plot_trace.loadTraces(traceFile)
  # return the voltage trace
  for trace in cppTraces:
    if trace['units'] == 'mV':
      trace['tol'] = tol
      trace['runTime'] = runTime
      os.remove(traceFile)
      return trace
    
  raise RuntimeError('No voltage trace produced by %s' % program)



###############################################################################
def getCppCurveTraces(baseDir):

  outFile = os.path.join(baseDir, 'cppcurve.json')
  try:
    trace_mtime = os.stat(outFile).st_mtime
    if _AlwaysPlotExistingTrace:
      trace_mtime = float('inf')
  except:
    trace_mtime = float('-inf')
    
  startupFile = os.path.join(baseDir, 'startup.txt')
  startup_mtime = os.stat(startupFile).st_mtime  
  
  if startup_mtime > trace_mtime:
    traces = []
    exponent = 2;
    frontList = [1]
    while True:
      
      # get the next tol
      if not frontList:
        if exponent > -6:
          #frontList = [1, 1.5, 2, 3.5, 5, 7.5]
          frontList = [1, 3]
        else:
          #frontList = [1, 2, 5]
          frontList = [1]
        exponent = exponent - 1
        if exponent < -15:
          break

      tol = float('%0.2ge%d' % (frontList.pop(), exponent))
      
      try:
        newTrace = simulateInCpp(baseDir, tol)
      except RuntimeError:
        break
      traces.append(newTrace)
      
      if traces[-1]['runTime'] >= 60 * _maxRunMinutes:
        break
    
    with open(outFile, 'w') as fOut:
      json.dump(traces, fOut)
  else:
    with open(outFile, 'r') as fIn:
      traces = json.load(fIn)
    
  badList = [];
  for trace in traces:
    numBad = sum([not y < float('inf') for y in trace['data']])
    if numBad > 0:
      badList.append(trace)
  
  for trace in badList:
    traces.remove(trace)
  
  return traces



###############################################################################
def getDifference(trace1, trace2):
  diffVec = [abs(d2 - d1) for (d2, d1) in zip(trace1['data'], trace2['data'])]
  return max(diffVec)



###############################################################################
def compareTraces(trace1, trace2):
  err = getDifference(trace1, trace2)
  tol = max(trace1['tol'], trace2['tol'])
  runTime = min(trace1['runTime'], trace2['runTime'])
  if err <= 0:
    err = 1.0e-20
  return (err, tol, runTime)



###############################################################################
def getCurve(traces):
  
  curve = { 'error' : [], 'tol' : [], 'runTime' : [] }
  
  for n in range(len(traces) - 1):
    (err, tol, runTime) = compareTraces(traces[n], traces[-1])
    curve['error'].append(err)
    curve['tol'].append(tol)
    curve['runTime'].append(runTime)
  
  return curve



###############################################################################
def fitCoefs(curveName, curve):
  keepInds = [n for n in range(len(curve['runTime'])) if \
              curve['runTime'][n] > 1 and curve['error'][n] > 0]
  t = [curve['runTime'][ind] for ind in keepInds]
  err = [curve['error'][ind] for ind in keepInds]
  
  
  
  coefs = numpy.polyfit(numpy.log(t), numpy.log(err), 1)
  desc = '%s error (mV) = (t/t0)^%g  t0 (s) = %g' % \
    (curveName, coefs[0], numpy.exp(-coefs[1] / coefs[0]))
  return desc



###############################################################################
def plotCurves(neuronCurve, cppCurve, markerSize=10.0, tickSize=24,\
               labelSize=30):
  mSize = 10.0
  override = {
   'fontsize'            : labelSize,
   'verticalalignment'   : 'center',
   'horizontalalignment' : 'center',
   'rotation'            : 'vertical'}
  
  fig = pyplot.figure()
  minTol = min([min(neuronCurve['tol']), min(cppCurve['tol'])])
  maxTol = max([max(neuronCurve['tol']), max(cppCurve['tol'])])
  pyplot.loglog([minTol, maxTol], [minTol, maxTol], 'k-', label='_nolegend_')
  pyplot.loglog(neuronCurve['tol'], neuronCurve['error'], 'bo', ms=markerSize,\
                label='NEURON')
  pyplot.loglog(cppCurve['tol'], cppCurve['error'], 'rs', ms=markerSize, \
                label='simulate_neuron.bin')
  pyplot.ylabel('Maximum Error (mV)', override)
  override['rotation'] = 'horizontal'
  pyplot.title('Error vs Tolerance', override)
  pyplot.xlabel('Tolerence', override)
  pyplot.legend(('NEURON', 'simulate_neuron.bin'), loc=0)
  axis = pyplot.gca();
  pyplot.setp(axis.get_xticklabels(), rotation='horizontal', fontsize=tickSize)
  pyplot.setp(axis.get_yticklabels(), rotation='horizontal', fontsize=tickSize)
  # reverse the x axis
  axis.set_xlim(axis.get_xlim()[::-1])

  fig = pyplot.figure()
  pyplot.loglog(neuronCurve['runTime'], neuronCurve['error'], 'bo', \
                ms=markerSize, label='NEURON')
  pyplot.loglog(cppCurve['runTime'], cppCurve['error'], 'rs', ms = markerSize,\
                label='simulate_neuron.bin')
  pyplot.title('Error vs Run Time', override)
  pyplot.xlabel('Run Time (s)', override)
  pyplot.legend( ('NEURON', 'simulate_neuron.bin'), loc=0)
  override['rotation'] = 'vertical'
  pyplot.ylabel('Maximum Error (mV)', override)
  axis = pyplot.gca();
  pyplot.setp(axis.get_xticklabels(), rotation='horizontal', fontsize=tickSize)
  pyplot.setp(axis.get_yticklabels(), rotation='horizontal', fontsize=tickSize)
  
  neuronDesc = fitCoefs('neuron', neuronCurve)
  cppDesc = fitCoefs('simulate_neuron.bin', cppCurve)
  top = max([max(neuronCurve['error']), max(cppCurve['error'])])
  bottom = min([min(neuronCurve['error']), min(cppCurve['error'])])
  
  left = min([min(neuronCurve['runTime']), min(cppCurve['runTime'])])
  right = max([max(neuronCurve['runTime']), max(cppCurve['runTime'])])
  x = left * (right/left)**0.6
  y = top * (bottom / top)**0.2
  pyplot.text(x, y, neuronDesc, fontsize=tickSize)
  y = top * (bottom / top)**0.4
  pyplot.text(x, y, cppDesc, fontsize=tickSize)



###############################################################################
def plotError(traces):
  # plot cpp error
  
  bestTrace = traces[-1]
  (dT, tUnits) = neuron_plot_trace.scaleTraceTime(bestTrace, 'ms')
  t = [dT * n for n in range(bestTrace['numT'])]
  
  fig = pyplot.figure()
  for n in range(len(traces) - 1):
    err = [v - vBest for (vBest, v) in zip(bestTrace['data'], traces[n]['data'])]
    pyplot.plot(t, err, '-', color=neuron_plot_trace.getColor(n % 31))
  
  pyplot.title('cpp error')
  

###############################################################################
def _parseArguments():
  arguments = sys.argv
  if len(arguments) > 2:
    print(_usageStr)
    sys.tracebacklimit = 1
    raise TypeError('Incorrect number of arguments.')
  elif len(arguments) == 2:
    baseDir = arguments[1]
  else:
    baseDir = os.getcwd()
  
  return baseDir


  
###############################################################################
if __name__ == "__main__":
  baseDir = _parseArguments()
  
  # get traces from simulation via NEURON
  neuronTraces = getNeuronCurveTraces(baseDir)
  
  # get traces from simulation via C++
  cppTraces = getCppCurveTraces(baseDir)
  
  # get the curve relating tol, accuracy, time from NEURON
  neuronCurve = getCurve(neuronTraces)
  # get the curve relating tol, accuracy, time via C++
  cppCurve = getCurve(cppTraces)
  
  # plot the curves
  plotCurves(neuronCurve, cppCurve)
  
  # plot the two best traces
  neuron_plot_trace.plotTrace(neuronTraces[-1], [cppTraces[-1]])
  
  # plot cpp error
  numError = min(20, len(cppTraces))
  plotError([cppTraces[n] for n in range(1 - numError, 0, 1)])
  #neuron_plot_trace.plotTrace(cppTraces[-1], cppTraces[-10:-1])

  # wait until figures are closed
  pyplot.show()
  
  sys.exit(0)
