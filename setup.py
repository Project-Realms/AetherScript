version = '0.3'

from setuptools import setup

setup(
	name='AetherX',
	version=version,
	description='The AetherScript Programming Language',
	long_description=open('README.md', 'r').read(),
	long_description_content_type='text/markdown',
	url='https://github.com/ProjectDragonRealms/AetherScript',
	author='Realms',
	author_email='dragonrealms2008@gmail.com',
	include_package_data=True,
	license='MIT',
	packages=['AetherX'],
	setup_requires=['pytest_runner'],
	scripts=[],
	tests_require=['pytest'],
	entry_points={},
	zip_safe=True,
	classifiers=[
		'Programming Language :: Python',
		'Programming Language :: Python :: 3',
		'Topic :: Software Development :: Libraries',
		'Topic :: Software Development :: Libraries :: Python Modules',
	],
)
