from setuptools import setup, find_packages

setup(
    # Basic info
    name='PyMetr',
    version='0.1.0',
    author='Ryan.C.Smith',
    author_email='bellstate@gmail.com',

    # A short description of the project
    description='A comprehensive Python library for connecting, controlling, and managing test and measurement instruments.',
    
    # A long description, can be the same as your GitHub README.md
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',  # This is important to render markdown correctly on PyPI

    # The project's main homepage.
    url='https://github.com/pymetr/pymetr',

    # Find all packages in the project
    packages=find_packages(),

    # What does your project relate to?
    keywords='instrumentation control SCPI test measurement plotting real-time data',
)
