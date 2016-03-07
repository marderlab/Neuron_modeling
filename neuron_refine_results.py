#!/usr/bin/python

_usageStr=\
"""usage: neuron_refine_results.py [startupFile] [resultsFile]
  Creates a new startup file that implements a fit centered closely on the
  results of a previous fit.
"""



import sys



###############################################################################
def refineLog(paramName, resultVal, nameLength):
  """
  Create a new fitting range for a log-distributed parameter
  """
  minRange = resultVal / 1.018
  maxRange = resultVal * 1.018
  minAllowed = resultVal / 2.0
  maxAllowed = resultVal * 2.0
  
  formatStr = '%%-%ds %%8.3g %%8.3g %%8.3g %%8.3g\n' % nameLength
  return formatStr % \
    (paramName, minAllowed, maxAllowed, minRange, maxRange)
    


###############################################################################
def refineUniform(paramName, resultVal, nameLength):
  """
  Create a new fitting range for a uniform-distributed parameter
  """
  minRange = resultVal - 0.5
  maxRange = resultVal + 0.5
  minAllowed = resultVal - 20.0
  maxAllowed = resultVal + 20.0
  
  formatStr = '%%-%ds %%8.1f %%8.1f %%8.1f %%8.1f\n' % nameLength
  return formatStr % \
    (paramName, minAllowed, maxAllowed, minRange, maxRange)




###############################################################################
def refineResults(startupFile, resultsFile):
  """
  Create a new startup file to do a follow-up fit centered around the results
  of a previous fit
  """
  results = {}
  maxNameLen = 0
  with open(resultsFile, 'r') as fIn:
    for line in fIn:
      try:
        paramName, paramValue = line.split()
        if paramName == 'value':
          continue
      except ValueError:
        continue
      
      results[paramName] = paramValue
      maxNameLen = max(maxNameLen, len(paramName))
  
  if startupFile == 'startup.txt':
    refineFile = startupFile + '.refine'
  else:
    refineFile = 'startup.txt'
  
  with open(startupFile, 'r') as fIn, open(refineFile, 'w') as fOut:
    for line in fIn:
      splitLine = line.split()
      if len(splitLine) in [3, 5] and splitLine[0] in results:
        # this is a fit parameter, refine it
        paramName = splitLine[0]
        resultVal = float(results[paramName])
        if float(splitLine[1]) * float(splitLine[2]) > 0:
          # this is a log distributed parameter
          outLine = refineLog(paramName, resultVal, maxNameLen)
        else:
          # this is a uniform-distributed parameter
          outLine = refineUniform(paramName, resultVal, maxNameLen)
        fOut.write(outLine)
      elif len(splitLine) == 5 and splitLine[0] == 'fit':
        # this line defines a fit, increase the control time by a factor of 4
        tauInd = line.rindex(splitLine[4])
        newTau = 4 * float(splitLine[4])
        outLine = line[0:tauInd] + '%.1f\n' % newTau
        fOut.write(outLine)
      else:
        # write out line as usual
        fOut.write(line)



###############################################################################
def _parseArguments():
  arguments = sys.argv
  if len(arguments) not in [1, 2, 3]:
    print(_usageStr)
    sys.tracebacklimit = 1
    raise TypeError('Incorrect number of arguments.')
  
  if len(arguments) >= 2:
    startupFile = arguments[1]
  else:
    startupFile = 'startup.txt'
  if len(arguments) == 3:
    resultsFile = arguments[2]
  else:
    resultsFile = 'results.txt'
  
  return startupFile, resultsFile


  
###############################################################################
if __name__ == "__main__":
  startupFile, resultsFile = _parseArguments()
  
  refineResults(startupFile, resultsFile)

  sys.exit(0)
