.PHONY: setup venv install run clean


# ============================================================
# OS DETECTION
# ============================================================

ifeq ($(OS),Windows_NT)

    DETECTED_OS := Windows
    PYTHON := python
    VENV_PYTHON := venv/Scripts/python.exe

else

    UNAME_S := $(shell uname -s)

    ifeq ($(UNAME_S),Darwin)
        DETECTED_OS := macOS
    else ifeq ($(UNAME_S),Linux)
        DETECTED_OS := Linux
    else
        DETECTED_OS := Unix
    endif

    PYTHON := python3
    VENV_PYTHON := venv/bin/python

endif


# ============================================================
# DEFAULT TARGET
# ============================================================

.DEFAULT_GOAL := setup


# ============================================================
# SETUP
# ============================================================

setup: venv install

	@printf "[INFO] OS: $(DETECTED_OS)\n\n"
	@printf "✅ Setup Complete\n\n"


# ============================================================
# CREATE VIRTUAL ENVIRONMENT
# ============================================================

venv:

ifeq ($(OS),Windows_NT)

	@if exist venv ( \
		echo [OK] Virtual environment already exists. \
	) else ( \
		echo [INFO] Creating virtual environment... && \
		$(PYTHON) -m venv venv || exit /b 1 \
	)

else

	@if [ -d "venv" ]; then \
		printf "[OK]  Virtual environment already exists.\n"; \
	else \
		printf "[INFO] Creating virtual environment...\n"; \
		$(PYTHON) -m venv venv || exit 1; \
		printf "[OK]  Virtual environment created.\n"; \
	fi

endif


# ============================================================
# INSTALL REQUIREMENTS
# ============================================================

install: venv

ifeq ($(OS),Windows_NT)

	@echo [INFO] Installing Python dependencies...
	@$(VENV_PYTHON) -m pip install -q  --upgrade pip
	@$(VENV_PYTHON) -m pip install -q  -r requirements.txt
	@echo [OK] Python dependencies installed.

else

	@printf "[INFO] Installing Python dependencies...\n"
	@$(VENV_PYTHON) -m pip install -q  --upgrade pip
	@$(VENV_PYTHON) -m pip install -q  -r requirements.txt
	@printf "[OK]  Python dependencies installed.\n"

endif


# ============================================================
# RUN MAIN PROGRAM
# ============================================================

run:

ifeq ($(OS),Windows_NT)

	@$(VENV_PYTHON) main.py

else

	@$(VENV_PYTHON) main.py

endif


# ============================================================
# CLEAN PYTHON CACHE
# ============================================================

clean:

ifeq ($(OS),Windows_NT)

	@echo Cleaning Python cache files...
	@for /R %%D in (__pycache__) do @if exist "%%D" rmdir /S /Q "%%D"
	@echo Done.

else

	@printf "[INFO] Cleaning Python cache files...\n"
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@printf "[OK]  Cleanup complete.\n"

endif