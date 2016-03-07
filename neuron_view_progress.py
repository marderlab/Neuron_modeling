#!/usr/bin/python

_usageStr=\
"""usage: neuron_plot_trace.py traceFile [traceFile2] [traceFile3] ...
         loads and plots the traces in specified trace files
"""



import sys
import os
import matplotlib.pyplot as pyplot
import scipy


###############################################################################
def getGenerationProgress(resumeFile):
  
  def _getProgress(splitLine, _numParams):
    err = float(splitLine[-_numParams - 1])
    try:
      uniformRange = float(splitLine[-_numParams - 2])
      logRange = float(splitLine[-_numParams - 3])
      fR = float(splitLine[-_numParams - 4])
      pR = max(uniformRange, scipy.log(logRange))
    except ValueError:
      fR = float('NaN')
      pR = float('NaN')
    return (err, fR, pR)
  
  def _getNextLine(_fIn):
    # get the next non-empty, non-comment line from file
    line = next(_fIn)[:-1].split('#')[0]
    while not line:
      line = next(_fIn)[:-1].split('#')[0]
    return line
  
  with open(resumeFile, 'r') as fIn:
    # get the number of parameters from the first line
    line = _getNextLine(fIn)
    numParams = int(line.split()[0])
    
    # skim through the parameter descriptions and other uninteresting stuff
    while 'generation history' not in line:
      line = next(fIn)
    
    # get the number of generations in the history
    numGenerations = int(line.split(None)[0])
    
    # get the generation history
    errors = scipy.ndarray(numGenerations)
    fRange = scipy.ndarray(numGenerations)
    pRange = scipy.ndarray(numGenerations)
    for genNum in range(numGenerations):
      line = _getNextLine(fIn)
      (errors[genNum], fRange[genNum], pRange[genNum]) = \
        _getProgress(line.split(None), numParams)
    
    # get the distribution of current errors
    line = _getNextLine(fIn)
    populationSize = int(line.split()[0])
    currentErrors = scipy.ndarray(populationSize)
    for n in range(populationSize):
      line = _getNextLine(fIn)
      currentErrors[n] = float(line.split()[0])
  
  return (errors, fRange, pRange, currentErrors)



###############################################################################
def plotProgress(errors, fRange, pRange, labelSize=22, tickSize=16):
  # make progress plot
  
  fig = pyplot.figure()
  #pyplot.gca().set_fontname('Helvetica') 
  genNum = scipy.arange(1, len(errors) + 1)
  pyplot.plot(genNum, errors, 'b-')
  if not scipy.isnan(fRange).all():
    pyplot.plot(genNum, fRange, 'r--')
    pyplot.plot(genNum, pRange, 'g--')
    pyplot.legend(('Best error', 'Error range', 'Parameters range'), loc=0, \
                  prop={'size' : labelSize})
    pyplot.ylabel('Error or Range', fontsize=labelSize)
    yMin = min(min(errors), min(fRange), min(pRange))
    yMax = max(max(errors), max(fRange))
    pMax = max(pRange)
    if pMax < 2 * yMax:
      yMax = pMax
    #pyplot.ylim(yMin, yMax)
  else:
    pyplot.legend(['Best error'], loc=0, prop={'size' : labelSize})
    pyplot.ylabel('Error', fontsize=labelSize)
  pyplot.xticks(fontsize=tickSize)
  pyplot.yticks(fontsize=tickSize)
  pyplot.title('Progress vs generation number', fontsize=labelSize)
  pyplot.xlabel('Generation number', fontsize=labelSize)
  
  #pyplot.ylim([0, max(errors)])
  pyplot.gca().set_yscale('log')



###############################################################################
def plotCurrentErrors(currentErrors, labelSize=22, barScale=1.0):
  # make histogram of current errors
  
  fig = pyplot.figure()
  
  numBins = max(20, round(scipy.sqrt(len(currentErrors))))
  hist, bins = scipy.histogram(currentErrors, bins=numBins)
  barWidth = barScale * (bins[1] - bins[0])
  binCenters = 0.5 * (bins[:-1] + bins[1:])
  pyplot.bar(binCenters, hist, align='center', width=barWidth)
  
  pyplot.ylabel('Number of parameter sets', fontsize=labelSize)
  pyplot.xlabel('Parameter set error')
  pyplot.title('Distribution of errors', fontsize=labelSize)



###############################################################################
def viewProgress(resumeFile):
  (errors, fRange, pRange, currentErrors) = getGenerationProgress(resumeFile)
  plotProgress(errors, fRange, pRange)
  plotCurrentErrors(currentErrors)
  # wait until figures are closed
  pyplot.show()


###############################################################################
def _parseArguments():
  arguments = sys.argv
  if len(arguments) > 2:
    print(_usageStr)
    sys.tracebacklimit = 1
    raise TypeError('Incorrect number of arguments.')
  elif len(arguments) == 2:
    resumeFile = arguments[1]
  else:
    resumeFile = 'resume.txt'
  
  return resumeFile


  
###############################################################################
if __name__ == "__main__":
  resumeFile = _parseArguments()
  
  viewProgress(resumeFile)

  sys.exit(0)
