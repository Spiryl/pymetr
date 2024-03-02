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

    # Classifiers help users find your project by categorizing it.
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
        
        # Indicate who your project is intended for
        'Intended Audience :: Engineers',
        'Topic :: Instrumentation :: Metrology',

        # Pick your license as you wish
        'License :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.11',
    ],

    # What does your project relate to?
    keywords='instrumentation control SCPI test measurement plotting real-time data',
)
