version = '0.0.1'

from setuptools import setup

setup(
	name='AetherX',
	version=version,
	description='The AetherScript programming language',
	url='https://github.com/ProjectDragonRealms/AetherScript',
	author='Realms',
	author_email='dragonrealms2008@gmail.com',
	packages=['AetherX'],
	include_package_data=True,
	license='MIT',
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
