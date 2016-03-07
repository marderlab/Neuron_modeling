#!/usr/bin/python3



_usageStr=\
"""usage: neuron_simulate.py startupFile [targetFile]
         Simulates the model defined/fit by startupFile
         if targetFile is specified, the model in startupFile is
            simulated against the voltage/current trace in targetFile."""



import sys, os, shutil, tempfile, time, math, neuron_createModelHocFile



class SimHocData:
  def __init__(self, modelFile, dataFile, traceFile, \
               sectionList, modelName, prefix, tol=None, integralStep=None, \
               useCVOde=True):
    self.setFileNames(modelFile, dataFile, traceFile, prefix)
    self.getTimeInfo()
    self.sectionList = sectionList
    self.modelName = modelName

    # allow setting
    self.tol = 1.0e-6
    self.integralStep = self.dt
    if tol != None:
      self.tol = tol
    if integralStep != None:
      self.integralStep = integralStep
    self.useCVOde = useCVOde



  def setFileNames(self, modelFile, dataFile, traceFile, prefix):
    self.modelFile = os.path.relpath(os.path.expanduser(modelFile))
    self.dataFile = os.path.relpath(os.path.expanduser(dataFile))
    if len(traceFile) == 0:
      self.traceFile = ""
    else:
      self.traceFile = os.path.abspath(os.path.expanduser(traceFile))
    splitModel = os.path.split(modelFile)
    self.simHocFile = os.path.join(splitModel[0], \
                                   prefix + splitModel[1])
    splitData = os.path.split(dataFile)
    self.simDataFile = os.path.join(splitModel[0], \
                                    prefix[0:3] + splitData[1])

  def getTimeInfo(self):
    with open(os.path.expanduser(self.dataFile), 'r') as h:
      line = next(h)
      self.numT = int(line)
      line = next(h)
      self.tStart = line.split(None)[0]
      for line in h:
        lastLine = line
        
    self.tFinal = lastLine.split(None)[0]
    self.dt = (float(self.tFinal) - float(self.tStart)) / (self.numT - 1)



  def writeSimHocFile(self):
    validate = (len(self.traceFile) > 0)
    _dT = str(self.integralStep)
    
    # figure out which traces must be recorded
    firstSec = self.sectionList[0].getFirstName()
    caSet = set(['Ca', 'CaU', 'CaS', 'CaT'])
    recordICa = False
    if len(caSet.intersection(set(self.sectionList[0].channelList))) > 0:
      # there is calcium in the first section
      firstSec = self.sectionList[0].getFirstName()
      if recordICa:
        traceNames = ['i_' + firstSec, 'v_' + firstSec, \
                      'CaInt_' + firstSec, 'iCa_' + firstSec]
      else:
        traceNames = ['i_' + firstSec, 'v_' + firstSec, 'CaInt_' + firstSec]

      neuronTraceNames = ['iRecord', 'vRecord', 'caRecord', 'iCaRecord']
      traceTargets = ['iInjector.i', 'modelCell.%s.v(0.5)' % firstSec, \
                      'modelCell.%s.Cai' % firstSec, \
                      'modelCell.%s.iCa' % firstSec]
      traceUnits = ['nA', 'mV', 'mM', 'nA']

    else:
      useCa = False
      neuronTraceNames = ['iRecord', 'vRecord']
      traceNames = ['i_' + firstSec, 'v_' + firstSec]
      traceTargets = ['iInjector.i', 'modelCell.%s.v(0.5)' % firstSec]
      traceUnits = ['nA', 'mV']
    
    with open(self.simHocFile, 'w') as f:
      f.write('secondorder = 2\n')
      if self.useCVOde:
        f.write('\nobjref cvode\n')
        f.write('cvode = new CVode()\n')
        f.write('cvode.active(1)\n')
        f.write('cvode.atol(%g)\n' % self.tol)
        f.write('cvode.rtol(%g)\n' % self.tol)
        f.write('cvode.maxstep(%g)\n' % self.integralStep)
        needInterpolate = False
      else:
        needInterpolate = (self.dt != self.integralStep)

      if needInterpolate:
        f.write('dt = %g\n' % self.integralStep)
      else:
        f.write('dt = %g\n' % self.dt)
      f.write('tStart = %s\n' % self.tStart)
      f.write('tFinal = %s\n' % self.tFinal)
      f.write('numT = %s\n' % self.numT)

      if validate:
        f.write('\nstrdef dataFile, modelFile, outFile, traceFile\n')
      else:
        f.write('\nstrdef dataFile, modelFile, outFile\n')
      f.write('dataFile = "%s"\n' % self.dataFile)
      f.write('modelFile = "%s"\n' % self.modelFile)
      f.write('outFile = "%s"\n' % self.simDataFile)
      if validate:
        f.write('traceFile = "%s"\n' % self.traceFile)

      f.write('\n// Load model hoc file:\n')
      f.write('load_file(modelFile)\n')
      f.write('objectvar modelCell\n')
      f.write('modelCell = new %s()\n' % self.modelName)

      f.write('\n// Get time/current trace of perturbing current injection:\n')
      #f.write('objref fileIn, tVec, iVec, vVec\n')
      f.write('objref fileIn, tVec, iVec\n')
      f.write('fileIn = new File()\n')
      f.write('fileIn.ropen(dataFile)\n')
  
      f.write('\nnumT = fileIn.scanvar()\n')
      f.write('startInd = modelCell.startInd\n')
      f.write('tVec = new Vector(numT - startInd)\n')
      f.write('iVec = new Vector(numT - startInd)\n')
      # don't keep voltage stored, explicitely throw it away
      #f.write('vVec = new Vector(numT - startInd)\n')
      f.write('for(i = 0; i <= startInd; i = i + 1){\n')
      f.write('  tVec.x[0] = fileIn.scanvar()\n')
      f.write('  iVec.x[0] = fileIn.scanvar()\n')
      # f.write('  vVec.x[0] = fileIn.scanvar()\n')
      f.write("  // don't record voltage, read and throw away\n")
      f.write('  dummyV    = fileIn.scanvar()\n')
      f.write('}\n')
      f.write('tStart = tVec.x[0]\n')
      f.write('tVec.x[0] = 0\n')
      f.write('printf("startInd = %d\\n", startInd)\n')
      f.write('printf("tStart = %d\\n", tStart)\n')
      f.write('for(i = startInd + 1; i < numT; i = i + 1){\n')
      f.write('  tVec.x[i - startInd] = fileIn.scanvar() - tStart\n')
      f.write('  iVec.x[i - startInd] = fileIn.scanvar()\n')
      #f.write('  vVec.x[i - startInd] = fileIn.scanvar()\n')
      f.write("  // don't record voltage, read and throw away\n")
      f.write('  dummyV    = fileIn.scanvar()\n')
      f.write('}\n')  
      f.write('fileIn.close()\n')
      f.write('numT = numT - startInd\n')
      f.write('printf("numT = %d\\n", numT)\n')  

      if validate:
        f.write('\n// Get error current data:\n')
        f.write('objref errVec\n')
        f.write('fileIn.ropen(traceFile)\n')
  
        f.write('\nnumErr = fileIn.scanvar()\n')
        f.write('errVec = new Vector(numErr - startInd)\n')
        f.write('for(i = 0; i < startInd; i = i + 1){\n')
        f.write('  errVec.x[0] = fileIn.scanvar()\n')
        f.write('}\n')
        f.write('for(i = startInd; i < numErr; i = i + 1){\n')
        f.write('  errVec.x[i - startInd] = -fileIn.scanvar()\n')
        f.write('}\n')
        f.write('fileIn.close()\n')
        f.write('numErr = numErr - startInd\n')
        f.write('printf("numErr = %d\\n", numErr)\n')        

      f.write('\n// Attach the stimulus current injector object:\n')
      f.write('objref iInjector\n')
      f.write('modelCell.%s iInjector = new IClamp(0.5)\n' % \
              self.sectionList[0].getFirstName())
      f.write('iInjector.del = 0\n')
      f.write('iInjector.dur = 1.0e9\n')
      f.write('// ...and inject the appropriate current trace:\n')
      f.write('iVec.play(&iInjector.amp, tVec, 1)\n')
      if validate:
        f.write('\n// Attach the error current injector object:\n')
        f.write('objref errInjector\n')
        f.write('modelCell.%s errInjector = new IClamp(0.5)\n' % \
                self.sectionList[-1].getLastName())
        f.write('errInjector.del = 0\n')
        f.write('errInjector.dur = 1.0e9\n')
        f.write('// ...and inject the appropriate current trace:\n')
        f.write('errVec.play(&errInjector.amp, tVec, 1)\n')      

      f.write('\n// Make some recording objects and record some waveforms:\n')
      f.write('objref tRecord\n')
      f.write('tRecord = new Vector()\n')
      f.write('tRecord.record(&t, dt)\n')
      for n in range(len(traceNames)):
        name_n = neuronTraceNames[n]
        target_n = traceTargets[n]
        f.write('objref %s\n' % name_n)
        f.write('%s = new Vector()\n' % name_n)
        f.write('%s.record(&%s, %s)\n' % (name_n, target_n, _dT))

      f.write('\n// Do the simulation:\n')
      f.write('tStop = tFinal - tStart + 0.5 * dt\n')
      f.write(r'printf("tStop: %d\n", tStop)')
      f.write('\n')
      f.write('modelCell.setState()\n')
      f.write('modelCell.setState()\n')  
      f.write('t = 0\n')
      f.write('while(t < tStop) {\n')
      f.write('  fadvance()\n')
      f.write('}\n')
      
      if needInterpolate:
        f.write('\n// Interpolate results:\n')
        f.write('objref interpVec\n')
        f.write('interpVec = new Vector()\n')
        f.write('interpVec = iRecord.c.interpolate(tVec, tRecord)\n')
        f.write('iRecord.copy(interpVec)\n')
        f.write('interpVec = vRecord.c.interpolate(tVec, tRecord)\n')
        f.write('vRecord.copy(interpVec)\n')
        f.write('interpVec = caRecord.c.interpolate(tVec, tRecord)\n')
        f.write('caRecord.copy(interpVec)\n')
        f.write('interpVec = iCaRecord.c.interpolate(tVec, tRecord)\n')
        f.write('iCaRecord.copy(interpVec)\n')
        f.write('tRecord.copy(tVec)\n')

      f.write('\n// Output results:\n')
      
      f.write('numTSim = vRecord.size()\n')
      f.write('printf("numTSim = %d\\n", numTSim)\n')

      f.write('\n//Output the results:\n')
      f.write('wopen(outFile)\n')
      f.write(r'fprint("# number of simulated traces\n")')
      f.write('\n')
      f.write(r'fprint("' + str(len(traceNames)) + r'\n")')
      f.write('\n')
      f.write(r'fprint("# name units numT deltaT\n")')
      f.write('\n')
      for n in range(len(traceNames)):
        name = traceNames[n]
        unit = traceUnits[n]
        f.write(r'fprint("' + name + r' ' + unit + r' %d ' + _dT + \
                r'\n", numTSim)')
        f.write('\n')
      for n in range(len(traceNames)):
        neuronName = neuronTraceNames[n]
        name = traceNames[n]
        unit = traceUnits[n]
        f.write(r'fprint("#' + name + r'\n")')
        f.write('\n')
        f.write('for(i = 0; i < numTSim; i = i + 1){\n')
        f.write(r'  fprint("%.19f\n", ' + neuronName + r'.x[i])')
        f.write('\n}\n')
        
      f.write('wopen()\n')



###############################################################################
def getParameters(paramFile):
  paramFile = os.path.expanduser(paramFile)
  if not os.path.isfile(paramFile):
    raise IOError('Parameter file %s does not exist.' % paramFile)

  pNames = []
  pVals = []
  with open(paramFile, 'r') as fIn:
    for line in fIn:
      
      # remove comments and endline
      line = line.split('#', 1)[0].strip('\n')

      # split line into words separated by white space      
      splitLine = line.split(None)
      
      if len(splitLine) == 2:
        # line should have a name followed by a parameter value
        pNames.append(splitLine[0])
        pVals.append(splitLine[1])
      elif len(splitLine) != 0:
        # doesn't describe a parameter and isn't empty
        raise IOError('Error reading parameter file ' + paramFile)

  return (pNames, pVals)



###############################################################################
def createTestStartup(startupFile, testFile, paramNames, paramVals):
  (startPath, startName) = os.path.split(os.path.abspath(startupFile))
  (testPath, testName) = os.path.split(testFile)
  tempStartupFile = os.path.join(tempfile.gettempdir(), startName)
  #testStartupFile = os.path.join(startPath, 'startup_' + testName)
  testStartupFile = os.path.join(startPath, 'startup.txt')
  homeDir = os.path.expanduser('~')
  
  #move original startup file to temporary name
  os.system('mv %s %s' % (startupFile, tempStartupFile))

  maxNameLen = 0
  for pName in paramNames:
    if len(pName) > maxNameLen:
      maxNameLen = len(pName)
  maxValLen = 0
  for pVal in paramVals:
    if len(pVal) > maxValLen:
      maxValLen = len(pVal)
      
  try:
    readHandle = open(tempStartupFile, 'r')
    writeHandle = open(testStartupFile, 'w')

    for line in readHandle:
      if '/home/tbrookin' in line:
        line = line.replace('/home/tbrookin', homeDir)
      if homeDir in line:
        line = line.replace(homeDir, '~')
      splitLine = line.split(None)
      if len(splitLine) == 0:
        writeLine = line
      else:
        firstWord = splitLine[0].lower()
        if firstWord == 'datafile':
          writeLine = line.replace(splitLine[1], \
                                   os.path.abspath(testFile)).\
                                   replace(homeDir, '~');
        elif firstWord == 'outputfile':
          outFile = os.path.join(startPath, 'output_' + testName)
          writeLine = line.replace(splitLine[1], outFile).\
                      replace(homeDir, '~')
        elif firstWord == 'resumefile':
          resumeFile = os.path.join(startPath, 'resume_' + testName)
          writeLine = line.replace(splitLine[1], resumeFile).\
                      replace(homeDir, '~');
        elif firstWord == 'populationsize':
          writeLine = line.replace(splitLine[1], '1')
        elif splitLine[0] in paramNames:
          ind = paramNames.index(splitLine[0])
          fStr = '%-*s  %*s %*s\n'
          writeLine = fStr % (maxNameLen, paramNames[ind], \
                              maxValLen, paramVals[ind], \
                              maxValLen, paramVals[ind])
        else:
          writeLine = line

      writeHandle.write(writeLine)

  finally:
    writeHandle.close()
    readHandle.close()
  return (tempStartupFile, testStartupFile, resumeFile, outFile)



###############################################################################
def makeResumeFile(resumeFile, paramVals):
  with open(os.path.expanduser(resumeFile), 'w') as fHandle:
    fHandle.write('PopulationSize: 1\n')
    fHandle.write('NumParameters:  %s\n' % len(paramVals))
    fHandle.write('\n')
    fHandle.write('CompletedGenerations: 0\n')
    fHandle.write('\n')
    fHandle.write('Total elapsed time: 0\n')
    fHandle.write('Generation elapsed time: 0\n')
    fHandle.write('\n')
    fHandle.write('BestValue: 9.9e99\n')
    fHandle.write('Best Parameters: ')
    for pVal in paramVals:
      fHandle.write(' ' + pVal)
    fHandle.write('\n')
    fHandle.write('\n')
    fHandle.write('Population:\n')
    fHandle.write('  nan')
    for pVal in paramVals:
      fHandle.write(' ' + pVal)
    fHandle.write('\n')



###############################################################################
def runFitneuron(startupFile, useValgrind=False, numProcessors=2):
  """runs fitneuron.bin (using valgrind if requested)
     if the requested startup file isn't startup.txt, then
       -if startup.txt exists, it is copied to a temporary file
       -tempStartupFile renamed startup.txt
       -after running fitneuron.bin, files are restored to their
         proper names"""
  (startPath, startupFileBase) = os.path.split(startupFile)
  homeDir = os.path.expanduser('~')
  binFile = os.path.join(homeDir, 'cpp', 'fitneuron', 'fitneuron.bin')

  if useValgrind:
    valgrindSuppFile = '/usr/local/share/openmpi/openmpi-valgrind.supp'
    valgrindStr = 'valgrind' + \
                  ' --suppressions=' + valgrindSuppFile + \
                  ' --leak-check=full' + ' '
  else:
    valgrindStr = ''

  # rename files if needed
  if startupFileBase != 'startup.txt':
    origFile = os.path.join(startPath, 'startup.txt')
    if os.path.exists(origFile):
      (tempFd, tempFileName) = tempfile.mkstemp(suffix='.txt')
      os.close(tempFd)
      shutil.move(origFile, tempFileName)
    else:
      tempFileName = None
    os.rename(startupFile, origFile)

  # run fitneuron.bin
  try:
    os.system('cd %s && mpirun -wdir %s -np %d %s%s' % \
              (startPath, startPath, numProcessors, valgrindStr, binFile))
  except Exception:  #generally only happens on Ctrl-C by user
    if startupFileBase != 'startup.txt':
      print('Restoring startup file structure.\n')
      os.rename(origFile, startupFile)
      if tempFileName != None:
        shutil.move(tempFileName, origFile)
    raise

  # restore files if needed
  if startupFileBase != 'startup.txt':
    os.rename(origFile, startupFile)
    if tempFileName != None:
      shutil.move(tempFileName, origFile)



###############################################################################
def restoreStartupFile(tempStartupFile, startupFile, testStartupFile, \
                       testFile):
  (startPath, testStartName) = os.path.split(testStartupFile)
  (testPath, testName) = os.path.split(testFile)
  newTestStartup = os.path.join(startPath, 'startup_' + testName)
  os.system('mv %s %s' % (testStartupFile, newTestStartup))
  os.system('mv %s %s' % (tempStartupFile, startupFile))
  return newTestStartup



###############################################################################
def removeTrashFiles(resumeFile, outFile):
  (resumePath, resumeName) = os.path.split(os.path.abspath(resumeFile))
  for file in os.listdir(resumePath):
    if os.path.split(file)[1].startswith(resumeName) and \
       not file.endswith('_trace.txt'):
      os.remove(file)
  os.remove(outFile)



###############################################################################
def elapsedTime(deltaT):
  #can get deltaT by difference between to calls to time.time()
  if deltaT < 60:
    tStr = '%g' % deltaT
    return tStr

  m = math.floor(deltaT / 60)
  s = deltaT - 60 * m
  if m < 60:
    tStr = '%dm %gs' % (m, s)
    return tStr

  h = math.floor(m / 60)
  m = m - 60 * h
  if h < 24:
    tStr = '%dh %dm %gs' % (h, m, s)
    return tStr

  d = math.floor(h / 24)
  h = h - 24 * d
  tStr = '%dd %dh %dm %gs' % (d, h, m, s)
  return tStr



###############################################################################
def simulateNeuron(startupFile, sectionList, modelName, \
                   tol=None, integralStep=None, useCVOde=True):
  fileNames = neuron_createModelHocFile.getFileNames(startupFile)
  hocFile = fileNames['hocFile']
  dataFile = fileNames['dataFile']
  traceFile = "" #don't use traceFile
  simHocData = SimHocData(hocFile, dataFile, traceFile, sectionList, \
                          modelName, 'Simulate', tol=tol, \
                          integralStep=integralStep, useCVOde=useCVOde)

  print('Simulating hoc file: %s' % os.path.relpath(simHocData.simHocFile))
  simHocData.writeSimHocFile()
  homeDir = os.path.expanduser('~')
  nrnScript = os.path.join(homeDir, 'python', 'neuron', 'ExecuteNrn.sh')
  startTime = time.time()
  returnStatus = os.system('%s %s' % (nrnScript, simHocData.simHocFile))
  if returnStatus != 0:
    raise RuntimeError('NEURON failed')
  runTime = time.time() - startTime
  print('Elapsed time: %s' % elapsedTime(runTime))
  return runTime



###############################################################################
def neuron_simulate(startupFile):
  (sectionList, modelName) = \
                neuron_createModelHocFile.createModelHocFile(startupFile)
  simulateNeuron(startupFile, sectionList, modelName)



###############################################################################
def neuron_simAgainst(startupFile, testDataFile):
  #1. Get model parameters from fit defined in startupFile
  #   a) Get dictionary of various data file names
  fileNames = neuron_createModelHocFile.getFileNames(startupFile)
  #   b) get the model parameters from paramFile
  (paramNames, paramVals) = getParameters(fileNames['paramFile'])

  #2. Get the model's start state for the test data file
  #   a) Create a startup file for the test data set with
  #       maxes and mins set to the model parameters (no new fitting)  
  (tempStartupFile, testStartupFile, resumeFile, outFile) = \
    createTestStartup(startupFile, testDataFile, paramNames, paramVals)
  #   b) Create a resume file with one parameter set in population
  #       (the fit values)
  makeResumeFile(resumeFile, paramVals)
  
  #   c) Call mpirun fitneuron with two processors
  runFitneuron(testStartupFile)
  

  #3. Restore startup files
  testStartupFile = restoreStartupFile(tempStartupFile, startupFile, \
                                       testStartupFile, testDataFile)

  #4. Simulate model against test file
  neuron_simulate(testStartupFile)

  #5. Remove resume files and output File
  removeTrashFiles(resumeFile, outFile)



###############################################################################
def _parseArguments():
  arguments = sys.argv
  if len(arguments) not in (2, 3):
    print(_usageStr)
    if len(arguments) > 1:
      raise TypeError('Incorrect number of arguments.')
    sys.exit(0)

  startupFile = arguments[1]
  if len(arguments) < 3:
    testDataFile = None
  else:
    testDataFile = arguments[2]
  
  return (startupFile, testDataFile)


  
###############################################################################
if __name__ == "__main__":
  (startupFile, testDataFile) = _parseArguments()

  if testDataFile == None:
    neuron_simulate(startupFile)
  else:
    neuron_simAgainst(startupFile, testDataFile)

  os.system('beep -l 50 -f 200')
  sys.exit(0)
