# microsetta-adminname: microsetta-admin CI

conda create --name test-microsetta-admin python=3.7
conda activate test-microsetta-admin
conda install --yes --file ci/conda_requirements.txt
pip install -r ci/pip_requirements.txt
make install
conda activate test-microsetta-admin

before make test, add:
conda install -c conda-forge nodejs

make test 
