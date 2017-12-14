#!/usr/bin/python

import subprocess, re, os
from navio.builder import task

@task()
def apidoc():
  """
  Generate API documentation using epydoc.
  """
  subprocess.call(["epydoc","--config","epydoc.config"])
    
@task()
def test(*args):
  """
  Run unit tests.
  """
  subprocess.call(["py.test"] + list(args))

@task()
def check_uncommited():
  result = subprocess.check_output(['git', 'status', '--porcelain'])
  if result:
    raise Exception('There are uncommited files')

@task()
def generate_rst():    
  subprocess.call(['pandoc', '-f', 'markdown', '-t', 'rst', '-o', 'README.rst', 'README.md'])
  subprocess.call(['pandoc', '-f', 'markdown', '-t', 'rst', '-o', 'CHANGES.rst', 'CHANGES.md'])
  subprocess.call(['git', 'commit', 'README.rst', 'CHANGES.rst', '-m', 'Autogenerated from markdown files'])

@task()
def update_version(ver = None):
  with open('navio/builder/__init__.py', 'r') as f:
    file_str = f.read()

  if not ver:
    regexp = re.compile('__version__\s*\=\s*\"([\d\w\.\-\_]+)\"\s*')
    m = regexp.search(file_str)
    if m:
      ver = m.group(1)
  
  minor_ver = int(ver[ver.rfind('.')+1:])
  ver = '{}.{}'.format(ver[:ver.rfind('.')], minor_ver+1)

  file_str = re.sub(
      '__version__\s*\=\s*\"([\d\w\.\-\_]+)\"\s*',
      '__version__ = "{}"\n'.format(ver),
      file_str)

  with open('navio/builder/__init__.py', 'w') as f:
    f.write(file_str)

  subprocess.call(['git', 'commit', 'navio/builder/__init__.py', '-m', 'Version updated to {}'.format(ver)])

@task()
def create_tag():
  with open('navio/builder/__init__.py', 'r') as f:
    file_str = f.read()
  regexp = re.compile('__version__\s*\=\s*\"([\d\w\.\-\_]+)\"\s*')
  m = regexp.search(file_str)
  if m:
    ver = m.group(1)
  else:
    raise "Can't find/parse current version in './navio/builder/__init__.py'"

  subprocess.call(['git', 'tag', '-a', '-m', 'Tagging version {}'.format(ver), ver])

@task()
def push():
  subprocess.call(['git', 'push', '--verbose'])
  subprocess.call(['git', 'push', '--tags', '--verbose'])

@task(generate_rst)
def upload():
  subprocess.call(['ssh-add', '~/.ssh/id_rsa'])
  subprocess.call(['python', 'setup.py', 'sdist', 'bdist_wininst', 'upload'])

@task()
def release(ver = None):
  check_uncommited()
  update_version(ver)
  create_tag()
  generate_rst()
  push()

@task(test)
def pypi():
  subprocess.call(['python', 'setup.py', 'sdist'])
  args = ['twine', 'upload']
  
  travis_pull_request = os.environ.get('TRAVIS_PULL_REQUEST', False) == 'true'
  travis_tag = os.environ.get('TRAVIS_TAG', False)
  
  if not travis_pull_request and travis_tag:
    args.append('--repository-url')
    args.append('https://upload.pypi.org/legacy/')
  else:
    args.append('--skip-existing')
    args.append('--repository-url')
    args.append('https://test.pypi.org/legacy/')

  args.append('dist/navio-builder-*')
  if subprocess.call(args):
    raise Exception('Error. Check logs above.')

__DEFAULT__ = test