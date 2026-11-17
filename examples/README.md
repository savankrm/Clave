# Use Clave credentials in a pytest test

From the repository root, install Clave with the test tools and run the example:

```console
python -m pip install -e ".[dev]"
python -m pytest examples/test_sample_login.py
```

You should see one passing test. Pytest finds the fixtures in `conftest.py`,
creates a temporary vault with a fake username and password, then passes the
credential to `test_sample_login.py`. The example uses a local stand-in for a
login and makes no network requests. Your regular vault stays untouched.

To adapt the example, replace the stand-in with your application's test login
and load credentials from your test vault. Keep real passwords out of test
code, logs, and failure messages.
