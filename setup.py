#!/usr/bin/env python3
''' Setup.py file '''
import setuptools


setuptools.setup(name='remote_gui',
      version='0.1',
      author='Marta Marczykowska-Gorecka',
      author_email='marmarta@invisiblethingslab.com',
      description='Qubes Remote Support GUI',
      license='GPL2+',
      url='https://www.qubes-os.org/',
      packages=["remote_gui"],
      entry_points={
          'gui_scripts': [
              'qubes-remote-support-gui = remote_gui.remote_gui:main',
          ]
      },
      package_data={'remote_gui': ["remote_gui.glade"]},
      # data_files=create_mo_files()
                 )
