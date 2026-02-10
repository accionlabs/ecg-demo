---
description: How to run ECL project commands using the correct Python environment
---

# ECL Python Environment

**ALWAYS** use the `ecl-demo` pyenv virtualenv for this project.

## Environment Details
- **Python version**: 3.12.12
- **Venv name**: `ecl-demo`
- **Managed by**: pyenv-virtualenv
- **Path**: `/Users/yakarteek/.pyenv/versions/ecl-demo/`
- **Pinned via**: `.python-version` file in project root

## Running Commands

// turbo-all

1. Activate the environment before any Python command:
```bash
eval "$(pyenv init -)" && eval "$(pyenv virtualenv-init -)" && pyenv activate ecl-demo
```

2. Or use the full path directly:
```bash
/Users/yakarteek/.pyenv/versions/ecl-demo/bin/python
/Users/yakarteek/.pyenv/versions/ecl-demo/bin/pip
/Users/yakarteek/.pyenv/versions/ecl-demo/bin/streamlit
```

3. Install packages:
```bash
/Users/yakarteek/.pyenv/versions/ecl-demo/bin/pip install <package>
```

4. Run Streamlit:
```bash
/Users/yakarteek/.pyenv/versions/ecl-demo/bin/streamlit run ecl_app.py
```

5. Run the ECL server:
```bash
/Users/yakarteek/.pyenv/versions/ecl-demo/bin/python ecl_server.py
```

6. Run tests:
```bash
/Users/yakarteek/.pyenv/versions/ecl-demo/bin/python -m pytest test_ecl.py -v
```

## IMPORTANT
- **NEVER** use bare `python3` or `pip3` — those point to system Python 3.9
- **ALWAYS** use the pyenv ecl-demo venv path or activate it first
