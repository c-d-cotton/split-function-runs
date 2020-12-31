#!/usr/bin/env python3
import os
from pathlib import Path
import sys

__projectdir__ = Path(os.path.dirname(os.path.realpath(__file__)) + '/')

import os
import shutil
import subprocess

def splitfunctionruns(functionpath, functionname, outputfolder, runlist, pythonpath = None, addbashfile = True, userelpath = False, labellist = None, createlabellist = False):
    """
    Multiprocessing doesn't always work so well, especially on a cluster.
    This function allows me to create separate files to run the same function for each element of a list.
    I tend to use this with qbus on a cluster.

    Also possible to specify the specific python path in a bash file.

    If userelpath is True then call pathtopythonfunction from a relativepath to the script location
    Otherwise, just use absolute paths. This might not work well if I want to generate the scripts on a different computer to where they are actually run.

    labellist are additional labels I use to help me identify different processes when I'm running them
    """
    # should delete old folder in case contains old runs
    if os.path.isdir(outputfolder):
        shutil.rmtree(outputfolder)
    try:
        os.makedirs(outputfolder)
    except Exception:
        None

    # if have 10 elements then go from 0 - 9 so only need lenid = 1
    # if have 11 elements then go from 0 - 10 so need lenid = 2
    lenids = len(str(len(runlist) - 1))

    if createlabellist is True:
        if labellist is not None:
            raise ValueError('Should not createlabellist since I specified a labellist.')
        labellist = []
        for element in runlist:
            if not isinstance(element, list):
                element = [element]
            labellist.append('_'.join([str(element_element) for element_element in element]))


    for i in range(0, len(runlist)):
        listelement = runlist[i]

        # if I have 20 elements in the list, I label them as p00, p01, ..., p19
        # adding the prefix zeroes ensures they run/display in the correct order
        thisid = 'p' + str(i).zfill(lenids)

        if labellist is not None:
            # add label
            thisid = thisid + '_' + labellist[i]

        # get output text for python file
        output = '#!/usr/bin/env python3\n'
        output = output + 'import os\n'
        output = output + 'import sys\n'
        if userelpath is True:
            pathtopythonfunction = os.path.relpath(os.path.dirname(functionpath), outputfolder)
            output = output + 'sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/" + "' + pathtopythonfunction + '")\n'
        else:
            output = output + 'sys.path.append("' + os.path.dirname(functionpath) + '")\n'
        output = output + 'from ' + os.path.basename(functionpath)[: -3] + ' import *\n'
        
        # if listelement is a string, str(['0.3']) should give "['0.3']"
        # if listelement is a float, str([0.3]) should give [0.3]
        # however doesn't work if listelement is a non-list string
        if isinstance(listelement, str):
            strlistelement = "'" + str(listelement) + "'"
        else:
            strlistelement = str(listelement)

        output = output + functionname + '(' + strlistelement + ')\n'

        pythonoutputpath = os.path.join(outputfolder, thisid + '.py')
        with open(pythonoutputpath, 'w+') as f:
            f.write(output)

        os.chmod(pythonoutputpath, 0o755)

        if addbashfile is True:
            # get text for bash file
            output = '#!/usr/bin/env bash\n'
            if pythonpath is None:
                pythonpath = 'python3'
            if userelpath is True:
                # define a variable localdir for local directory
                output = output + '''localdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"''' + '\n'
                output = output + pythonpath + ' ' + '"$localdir"/' + thisid + '.py\n'
            else:
                output = output + pythonpath + ' ' + os.path.join(outputfolder, thisid + '.py\n')

            bashoutputpath = os.path.join(outputfolder, thisid + '.sh')
            with open(bashoutputpath, 'w+') as f:
                f.write(output)

            os.chmod(bashoutputpath, 0o755)


# Test:{{{1
def test_aux(i):
    with open(__projectdir__ + os.path.join('test', 'output', str(i) + '.txt'), 'w+') as f:
        f.write(str(i))


def test():
    runlist = list(range(11))

    splitfunctionruns(__projectdir__ / Path('splitfunctionruns_func.py'), 'test_aux', __projectdir__ + os.path.join('test', 'output'), runlist, createlabellist = True)

# Qsub:{{{1
def qsubfolder(folder, qsubcommand = None, setoutputfolder = True):
    """
    qsub -M e-mail -m beas -l mem_free=500M filename
    -m beas means send an e-mail on occurrences of begin/end/abort/suspend

    -l is requirements for processing power mem_free is RAM etc. It is per processor
    can use mem_free or h_vmem to specify memory - mem_free means that amount of memory must be available on the server while h_vmem means the job gets killed if it exceeds this memory
    """

    files = sorted(os.listdir(folder))
    bashfiles = [filename for filename in files if filename.endswith('.sh')]

    if qsubcommand is None:
        qsubcommand = 'qsub '

    if setoutputfolder is True and ' -o ' not in qsubcommand and ' -e ' not in qsubcommand:
        qsubcommand = qsubcommand + ' -o ' + folder
        qsubcommand = qsubcommand + ' -e ' + folder

    for bashfile in bashfiles:
        subprocess.call(qsubcommand + ' ' + os.path.join(folder, bashfile), shell = True)


