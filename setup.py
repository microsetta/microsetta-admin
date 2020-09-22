# ----------------------------------------------------------------------------
# Copyright (c) 2019-, The Microsetta Initiative development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

from setuptools import setup, find_packages

import versioneer

setup(
    name="microsetta-admin",
    author="Daniel McDonald",
    author_email="danielmcdonald@ucsd.edu",
    packages=find_packages(),
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    url="https://github.com/biocore/microsetta-admin",
    description="A RESTful API to support The Microsetta Initiative",
    license='BSD-3-Clause',
    package_data={'microsetta_admin': [
        'server_config.json',
        'templates/*.*',
        'static/*',
        'static/css/*',
        'static/img/*',
        'static/vendor/*',
        'static/vendor/bootstrap-4.4.1-dist/css/*',
        'static/vendor/bootstrap-4.4.1-dist/js/*',
        'static/vendor/DataTables/*',
        'static/vendor/DataTables/Buttons-1.6.2/*',
        'static/vendor/DataTables/Buttons-1.6.2/css/*',
        'static/vendor/DataTables/Buttons-1.6.2/js/*',
        'static/vendor/DataTables/Buttons-1.6.2/swf/*',
        'static/vendor/DataTables/DataTables-1.10.21/*',
        'static/vendor/DataTables/DataTables-1.10.21/css/*',
        'static/vendor/DataTables/DataTables-1.10.21/images/*',
        'static/vendor/DataTables/DataTables-1.10.21/js/*',
        'static/vendor/DataTables/FixedColumns-3.3.1/*',
        'static/vendor/DataTables/FixedColumns-3.3.1/css/*',
        'static/vendor/DataTables/FixedColumns-3.3.1/jss/*',
        'authrocket.pubkey']},
)
