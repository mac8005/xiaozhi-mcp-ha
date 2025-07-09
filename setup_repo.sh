#!/bin/bash

# Script to set up the GitHub repository for Xiaozhi MCP Home Assistant integration

echo "Setting up Xiaozhi MCP Home Assistant integration repository..."

# Initialize git repository
git init

# Create .gitignore
cat > .gitignore << EOF
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# celery beat schedule file
celerybeat-schedule

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# Home Assistant
secrets.yaml
known_devices.yaml
.uuid
.HA_VERSION
.cloud
.storage
deps
tts
www
OZW_Log.txt
home-assistant.log
home-assistant_v2.db
*.conf
*.pid
*.xml
*.crt
*.key
*.pem
*_keyfile.json
*.google.token

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# macOS
.DS_Store
.AppleDouble
.LSOverride

# Windows
Thumbs.db
ehthumbs.db
Desktop.ini

# Linux
*~

# Test files
test_config/
EOF

# Add all files
git add .

# Initial commit
git commit -m "Initial commit: Xiaozhi MCP Home Assistant integration"

echo "Repository setup complete!"
echo ""
echo "Next steps:"
echo "1. Create a new repository on GitHub named 'xiaozhi-mcp-hacs'"
echo "2. Add remote origin: git remote add origin https://github.com/mac8005/xiaozhi-mcp-hacs.git"
echo "3. Push to GitHub: git push -u origin main"
echo "4. Create a release to make it available via HACS"
echo ""
echo "Don't forget to:"
echo "- Test the integration thoroughly before releasing"
echo "- Update the version numbers as needed"
echo "- Configure GitHub Actions secrets if needed"
echo "- Ensure the Home Assistant MCP Server integration is installed and configured"
EOF
