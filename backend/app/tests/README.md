
## Running all tests

To run the tests from the root directory of the project, you can use the following command:

```bash
$ pytest backend/app/tests
```

To run the tests in the `tests` directory, you can use the following command:

```bash
$ pytest .
```

These commands will run all the tests in the `backend/app/tests` directory.

## Running specific tests

To run specific tests, you can specify the path to the test file or directory. For example, to run the tests in the `test_exemple.py` file, you can use the following command:

```bash
$ pytest backend/app/tests/test_exemple.py
```

To run the tests in the `test_exemple` directory, you can use the following command:

```bash
$ pytest test_exemple.py
``` 
