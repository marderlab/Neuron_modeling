#!/usr/bin/python


_usageStr=\
"""usage: test_params.py
         blah
"""



import sys, os
import matplotlib.pyplot as pyplot
import neuron_createModelHocFile
import neuron_simulate
import neuron_plot_trace



###############################################################################
def getNeuronTraceFile(startupFile, fileNames):
  dataFile = fileNames['dataFile']
  splitData = os.path.split(dataFile)
  return os.path.join(splitData[0], 'Sim' + splitData[1])



###############################################################################
def simulateInNeuron(baseDir):
  # point to the startup file
  startupFile = os.path.join(baseDir, 'start_neuron.txt')
  # get info about other files associated with the simulation
  fileNames = neuron_createModelHocFile.getFileNames(startupFile)
  # get the name of the file containing the output traces
  traceFile = getNeuronTraceFile(startupFile, fileNames)
  
  # run the simulation
  startup_mtime = os.stat(startupFile).st_mtime
  geo_mtime = os.stat(fileNames['geoFile']).st_mtime
  try:
    trace_mtime = os.stat(traceFile).st_mtime
  except:
    trace_mtime = float('-inf')
  if startup_mtime > trace_mtime or geo_mtime > trace_mtime:
    # need to simulate
    neuron_simulate.neuron_simulate(startupFile)
  
  # load the output traces
  neuronTraces = neuron_plot_trace.loadTraces(traceFile)
  # scale any current traces by -1
  #for trace in neuronTraces:
  #  if trace['units'] == 'nA':
  #    trace['data'] = [-x for x in trace['data']]
  # and return them
  return neuronTraces



###############################################################################
def simulateInCpp(baseDir):
  # point to the startup file and the output trace file
  programFile = os.path.abspath(os.path.join(baseDir, 'simulate_neuron.bin'))
  startupFile = os.path.join(baseDir, 'startup.txt')
  traceFile = os.path.join(baseDir, 'recorded_traces.txt')
  
  
  # run the simulation
  startup_mtime = os.stat(startupFile).st_mtime
  try:
    trace_mtime = os.stat(traceFile).st_mtime
  except:
    trace_mtime = float('-inf')
  if startup_mtime > trace_mtime:
    # need to simulate
    os.system('%s %s %s' % (programFile, startupFile, traceFile) )
  
  # load the output traces
  cppTraces = neuron_plot_trace.loadTraces(traceFile)
  #print('Loaded %d cpp traces' % len(cppTraces))
  # and return them
  return cppTraces



###############################################################################
def checkDifference(neuronTrace, cppTraces, traces):
  for cppTrace in cppTraces:
    if cppTrace['name'] == (neuronTrace['name'] + '_0'):
      # these traces record the same thing. Plot:
      #   -both traces overlayed
      #   -their difference (if they have the same length)

      # remove them from the general plot
      traces.remove(neuronTrace)
      traces.remove(cppTrace)
      
      # plot the traces overlayed
      neuron_plot_trace.plotTrace(neuronTrace, cppTrace)
      
      
      neuronData = neuronTrace['data']
      cppData = cppTrace['data']
      if len(neuronData) != len(cppData):
        # the traces have different lengths, don't try to form difference
        return
      
      # form the difference between them and plot it
      diffData = [neuronData[n] - cppData[n] for n in range(len(neuronData))]
      diffTrace = {'name'  : neuronTrace['name'] + '_difference', \
                   'units' : neuronTrace['units'], \
                   'numT'  : neuronTrace['numT'], \
                   'dT'    : neuronTrace['dT'], \
                   'data'  : diffData}
      neuron_plot_trace.plotTrace(diffTrace)
      
      return



###############################################################################
def compareTraces(neuronTraces, cppTraces):
  # join the two lists of traces
  traces = []
  traces.extend(neuronTraces)
  traces.extend(cppTraces)
  
  for neuronTrace in neuronTraces:
    checkDifference(neuronTrace, cppTraces, traces)
  
  return traces
  


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
  neuronTraces = simulateInNeuron(baseDir)
  
  # get trace from simulation via C++
  cppTraces = simulateInCpp(baseDir)
  
  # join traces, and make difference trace for v_soma
  traces = compareTraces(neuronTraces, cppTraces)
  
  for trace in traces:
    # plot each trace
    neuron_plot_trace.plotTrace(trace)
    
  # wait until figures are closed
  os.system('beep -l 100 -f 200 -n 2')
  pyplot.show()

  sys.exit(0)
