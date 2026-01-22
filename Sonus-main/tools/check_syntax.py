import py_compile
import glob
import sys

files = glob.glob('src/**/*.py', recursive=True)
print('Checking', len(files), 'files')
errs = 0
for f in files:
    try:
        py_compile.compile(f, doraise=True)
    except Exception as e:
        print('ERROR', f, ':', e)
        errs += 1
sys.exit(errs)
