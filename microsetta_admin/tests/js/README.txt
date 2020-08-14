To run locally, you'll need to install node/npm, this will then be used to
install qunit and all dependencies. You can then run make test, or if you just
want the javascript tests, run_js_tests.sh at the root of the repo.

Note that there is a compromise made to enable testing by command line: any
testable functions must be retrievable through node. This means declaring them
in the node defined module.exports field at the bottom of js files.
Since the browser has no concept of module.exports, you must check for existence
before setting this field. For a simple example of this, see

  * microsetta_admin/static/js/testable.js.

In the future, if you want to update qunit, you don't need to (and shouldn't)
commit node_modules to the repo.

Instead:

cd <repo root>/microsetta_admin/tests/js/         (Goes to this folder)
npm install qunit                                 (Builds the node_modules folder and updates contents of package-lock.json)
git add package-lock.json                         (Adds package-lock.json)
git commit                                        (Commits package-lock.json)

Note that run_js_tests.sh will use npm ci to reproduce whatever is specified by
the package-lock file.

The package-lock.json defines the exact node package configuration that is used
by travis, so the build will automatically update to use your new configuration.
