#!/usr/bin/python



_usageStr=\
"""usage: neuron_recalcResume.py resumeFile
        Back up resumeFile to resumeFile.backup then overwrite parameter values
        with NaN, so that parameters will be re-calculated.
"""



import os, sys



###############################################################################
def makeBackupFile(resumeFile):
  """
  backup resumeFile and return the name of the backup file
  """
  backupFile = resumeFile + '.backup'
  if os.path.isfile(backupFile):
    sys.tracebacklimit = 0
    raise TypeError('Backup file already exists: ' + backupFile)
  os.rename(resumeFile, backupFile)
  return backupFile



###############################################################################
def getNext(fIn, fOut):
  line = next(fIn)
  while (not line.strip()) or (line.strip().startswith('#')):
    fOut.write(line)
    line = next(fIn)
  return line



###############################################################################
def rewriteHeaderLines(fIn, fOut, newPopulationSize):
  # get the paramteter descriptions
  firstLine = getNext(fIn, fOut)
  numDesc = int(firstLine.split(None, 1)[0])
  fOut.write(firstLine)
  for n in range(numDesc):
    fOut.write(getNext(fIn, fOut))
  
  # set the best parameters' value to Inf
  line = getNext(fIn, fOut)
  val = line.split(None, 1)[0]
  fOut.write(line.replace(val, 'inf'))
  
  # write the total time without altering it
  fOut.write(getNext(fIn, fOut))
  # set the current generation time to 0
  line = getNext(fIn, fOut)
  timeStr = line.split('#')[0].strip()
  fOut.write(line.replace(timeStr, '0.0s', 1))
  
  # write the number of parameter sets evaluated without altering it
  fOut.write(getNext(fIn, fOut))
  # set the number of evaluations this generation to 0
  line = getNext(fIn, fOut)
  numEval = line.split(None, 1)[0]
  fOut.write(line.replace(numEval, '0', 1))
  
  # write the rest of the header without altering it, until the line declaring
  # the population size
  line = getNext(fIn, fOut)
  while not line.endswith('# population\n'):
    fOut.write(line)
    line = getNext(fIn, fOut)

  # set the new population size (if requested) and write last header line
  if newPopulationSize < float('inf'):
    splitLine = line.split()
    oldPop = splitLine[0]
    line = line.replace(oldPop, str(newPopulationSize), 1)
  fOut.write(line)



###############################################################################
def rewritePopulation(fIn, fOut, newPopulationSize):
  n = 0
  for line in fIn:
    n += 1
    if n > newPopulationSize:
      break
    
    # replace value with nan
    valueStr = line.split(None, 1)[0]
    fixedLine = line.replace(valueStr, 'nan', 1)
    fOut.write(fixedLine)



###############################################################################
def writeNewResumeFile(resumeFile, backupFile, newPopulationSize=None):
  """
  read from backupFile and write a new resumeFile where all the parameters need
  to be reevaluated
  """
  if newPopulationSize is None:
    newPopulationSize = float('inf')
  
  with open(resumeFile, 'w') as fOut, open(backupFile, 'r') as fIn:
    rewriteHeaderLines(fIn, fOut, newPopulationSize)
        
    rewritePopulation(fIn, fOut, newPopulationSize)




###############################################################################
def recalcResume(resumeFile, newPopulationSize=None):
  """
  backup resumeFile and write a new resumeFile where all the parameters need to
  be reevaluated
  """
  backupFile = makeBackupFile(resumeFile)
  
  try:
    writeNewResumeFile(resumeFile, backupFile, newPopulationSize)
  except:
    os.system('rm -f %s' % resumeFile)
    os.system('mv %s %s' % (backupFile, resumeFile))
    raise



###############################################################################
def _parseArguments():
  arguments = sys.argv
  
  if len(arguments) > 3:
    print(_usageStr)
    sys.tracebacklimit = 0
    raise TypeError('Incorrect number of arguments.')
  
  resumeFile = arguments[1]
  if not os.path.isfile(resumeFile):
    print(_usageStr)
    sys.tracebacklimit = 0
    raise TypeError("File doesn't exist: " + resumeFile)
  
  if len(arguments) == 3:
    populationSize = int(arguments[2])
  else:
    populationSize = float('inf')
  
  return resumeFile, populationSize



###############################################################################
if __name__ == "__main__":
  resumeFile, populationSize = _parseArguments()
  
  recalcResume(resumeFile, populationSize)
  
  sys.exit(0)

