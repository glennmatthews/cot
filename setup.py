from setuptools import setup
import os.path

execfile(os.path.join(os.path.dirname(__file__), 'COT', '__version__.py'))

README_FILE = os.path.join(os.path.dirname(__file__), 'README.md')

setup(
    name='common-ovf-tool',
    version=__version__,
    author='Glenn Matthews',
    author_email='glmatthe@cisco.com',
    packages=['COT'],
    entry_points = {
        'console_scripts': [
            'cot = COT.cli:main',
        ],
    },
    url='TODO',
    license='LICENSE.txt',
    description='Common OVF Tool',
    long_description=open(README_FILE).read(),
    test_suite='COT.tests',
)
