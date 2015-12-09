Syllabus gathering and visualisation tool
=========================================

# Installing

The following libraries are required:

- libgts
- graphviz*
- libxslt
- libxml

The following npm packages are required:

- Babel
- Bower

To install, do the following:

1. Clone the repository
2. Install pip dependencies from `server/requirements.txt` (preferably, using virtualenv)
3. Install bower dependencies to `client/components` using `client/bower.json`
4. Run babel to compile JS:

   ``` 
   babel -o client/js_dist/syllabus.js client/js 
   ```
5. Create `server.cfg`, setting `SQLALCHEMY_DATABASE_URI` variable, which specifies the database to use**

For debugging, run:
``` 
python server/debug.py 
```

This will run standalone Flask server, which you can connect to locally.

Otherwise, for production, use uWSGI, and point it to the `app` from `server/server.py`.

(*) Graphviz should be compiled with GTS support enabled, otherwise graphs might look weird. In Ubuntu, the only way to do that is to install libgts dev libraries, and compile/install Graphiz manually. For OS X, use `--with-gts` homebrew flag when installing graphviz.

(**) E.g. for SQLite database:

```
SQLALCHEMY_DATABASE_URI = "sqlite:////Users/artur/syllabus.db"
```

Various other configuration variables are available. Full list provided in [http://flask.pocoo.org/docs/0.10/config/#builtin-configuration-values](flask documentation).

# Creating initial database

`add_initial_data.py` script could be used to create initial database using the files from `initial_data` folder. For usage instructions, run

```python add_initial_data.py -h```

