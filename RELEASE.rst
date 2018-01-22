Releasing a new version
=======================

1. Remove -dev from the version
2. Commit "Releasing version"
3. Add tag with version number
4. `flit wheel --upload`
5. Increase version number and add -dev
6. Commit "Bump version"
