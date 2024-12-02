Simple Flask Project That runs background jobs and queues
the system requires to be run on virtual environment so to set a virtual environment we first need to install the "virtualenv" package to install that use this command

```bash
pip install virtualenv

```

than

```bash
python3 -m venv myenv

```

If you're using Python 2 (with virtualenv):

```bash
virtualenv myenv

```

then to run the project activate the virtual environment

On Windows:

```bash
myenv\Scripts\activate

```

On macOS/Linux:

```bash
source myenv/bin/activate

```

# start

```bash
python app.py

```

# start worker

```bash
rq worker

```

To deactivate the virtual environment and return to your system's default Python environment, simply run

```bash
deactivate

```
