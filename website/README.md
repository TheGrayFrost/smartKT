# Using Python and Javascript together with Flask

## Quickstart

Requirements: (see requirements.txt)

Edit the `web_config.json`

``` bash
$ cat web_config.json
$ python3 initialize.py
$ export FLASK_APP=app.py
$ flask run
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
```

Open http://127.0.0.1:5000/

## Overview

Running `initialize.py` generates all the required files for starting the server.
The details of the execution flow has been documented by the submission from Prachi

## Details

Please see `docs/` folder. For explanations on the server, refer comments inside
the code. For details on algorithms of the various graphs (except CFG) and
implementations of interactive graphs, please refer the thesis.
