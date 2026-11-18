# Day 1

- What I set up: a local git repository, an isolated Python environment with uv,
  ruff for linting, and pre-commit so the checks run before every commit. Created
  the GitHub repo and pushed the first commit.
- What each file is for:
  - pyproject.toml: the project's ID card. Its name, the libraries it needs, and
    the linter settings.
  - .gitignore: the list of things git must never track (raw data, the virtual
    environment, cache files).
  - .pre-commit-config.yaml: checks that run automatically before each commit.
  - Makefile: shortcuts, so `make test` stands for a longer command.
  - LICENSE: tells others how they may reuse the code.
- What confused me: the difference between the Terminal app and the terminal inside
  VS Code, and that GitHub is only the online copy while the work happens on my Mac.
- Check: data/raw/ is in .gitignore because the raw files are about 2 GB, too big
  for git, and anyone can re-download them with a script. Git should track what I
  wrote, not what a script can rebuild.
