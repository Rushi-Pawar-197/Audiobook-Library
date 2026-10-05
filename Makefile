.PHONY: setup venv system-deps install run doctor clean

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

# SYSTEM DEPENDENCIES

# ============================================================

system-deps:

ifeq ($(OS),Windows_NT)

@echo [INFO] Checking system dependencies...
@where ffmpeg >nul 2>nul && where ffprobe >nul 2>nul || ( \
	echo [ERROR] FFmpeg and FFprobe were not found. && \
	echo [INFO] Please install FFmpeg and ensure ffmpeg and ffprobe are available in PATH. && \
	exit /b 1 \
)
@echo [OK] System dependencies available.


else ifeq ($(UNAME_S),Darwin)


	@if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then \
		printf "[OK]  System dependencies available.\n"; \
	else \
		printf "[INFO] System dependencies missing. Installing FFmpeg...\n"; \
		if command -v brew >/dev/null 2>&1; then \
			brew install ffmpeg || exit 1; \
		else \
			printf "[ERROR] Homebrew is required to install FFmpeg automatically.\n"; \
			printf "[INFO] Please install FFmpeg manually and run make setup again.\n"; \
			exit 1; \
		fi; \
		if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then \
			printf "[OK]  System dependencies installed.\n"; \
		else \
			printf "[ERROR] FFmpeg installation completed, but ffmpeg or ffprobe is not available in PATH.\n"; \
			exit 1; \
		fi; \
	fi


else ifeq ($(UNAME_S),Linux)


	@if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then \
		printf "[OK]  System dependencies available.\n"; \
	else \
		printf "[INFO] System dependencies missing. Installing FFmpeg...\n"; \
		if command -v apt-get >/dev/null 2>&1; then \
			sudo apt-get update && sudo apt-get install -y ffmpeg || exit 1; \
		elif command -v dnf >/dev/null 2>&1; then \
			sudo dnf install -y ffmpeg || exit 1; \
		elif command -v pacman >/dev/null 2>&1; then \
			sudo pacman -Sy --noconfirm ffmpeg || exit 1; \
		else \
			printf "[ERROR] Unsupported package manager.\n"; \
			printf "[INFO] Please install FFmpeg manually and run make setup again.\n"; \
			exit 1; \
		fi; \
		if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then \
			printf "[OK]  System dependencies installed.\n"; \
		else \
			printf "[ERROR] FFmpeg installation completed, but ffmpeg or ffprobe is not available in PATH.\n"; \
			exit 1; \
		fi; \
	fi


else


@printf "[WARNING] Automatic system dependency installation is not supported on this OS.\n"
@printf "[INFO] Please ensure ffmpeg and ffprobe are installed and available in PATH.\n"


endif



# ============================================================
# DEFAULT TARGET
# ============================================================

.DEFAULT_GOAL := setup


# ============================================================
# SETUP
# ============================================================

setup: system-deps venv install

	@printf "[INFO] OS: $(DETECTED_OS)\n\n"
	@printf "✅ Setup Complete\n\n"


# ============================================================
# CREATE / VALIDATE VIRTUAL ENVIRONMENT
# ============================================================

venv:

ifeq ($(OS),Windows_NT)

	@if exist venv\Scripts\python.exe ( \
		venv\Scripts\python.exe -m pip --version >nul 2>nul \
		if errorlevel 1 ( \
			echo [WARNING] Virtual environment is incomplete or unusable. && \
			echo [INFO] Removing broken virtual environment... && \
			rmdir /S /Q venv && \
			echo [INFO] Creating virtual environment... && \
			$(PYTHON) -m venv venv || exit /b 1 \
		) else ( \
			echo [OK] Virtual environment is healthy. \
		) \
	) else ( \
		if exist venv (echo [WARNING] Virtual environment is incomplete or unusable. && rmdir /S /Q venv) \
		echo [INFO] Creating virtual environment... && \
		$(PYTHON) -m venv venv || exit /b 1 \
	)

else

	@if [ -x "$(VENV_PYTHON)" ] && "$(VENV_PYTHON)" -m pip --version >/dev/null 2>&1; then \
		CURRENT_PY=$$($(PYTHON) -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'); \
		VENV_PY=$$($(VENV_PYTHON) -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'); \
		if [ "$$CURRENT_PY" = "$$VENV_PY" ]; then \
			printf "[OK]  Virtual environment is healthy (Python $$VENV_PY).\n"; \
		else \
			printf "[WARNING] Virtual environment uses Python $$VENV_PY, current Python is $$CURRENT_PY.\n"; \
			printf "[INFO] Recreating virtual environment...\n"; \
			rm -rf venv; \
			$(PYTHON) -m venv venv || exit 1; \
			printf "[OK]  Virtual environment recreated.\n"; \
		fi; \
	else \
		if [ -d "venv" ]; then \
			printf "[WARNING] Virtual environment is incomplete or unusable.\n"; \
			printf "[INFO] Removing broken virtual environment...\n"; \
			rm -rf venv; \
		fi; \
		printf "[INFO] Creating virtual environment...\n"; \
		$(PYTHON) -m venv venv || { \
			printf "[ERROR] Could not create the virtual environment.\n"; \
			printf "[INFO] Your Python installation may be missing its venv package.\n"; \
			exit 1; \
		}; \
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
# ENVIRONMENT DIAGNOSTICS
# ============================================================

doctor:

ifeq ($(OS),Windows_NT)

	@echo.
	@echo Audiobook Library Environment
	@echo ============================
	@echo OS: $(DETECTED_OS)
	@$(PYTHON) --version
	@if exist venv\Scripts\python.exe ( \
		echo Venv: present && \
		venv\Scripts\python.exe --version && \
		venv\Scripts\python.exe -m pip --version || exit /b 1 \
	) else ( \
		echo Venv: MISSING && exit /b 1 \
	)
	@if exist requirements.txt (echo Requirements: present) else (echo Requirements: MISSING && exit /b 1)
	@where ffmpeg >nul 2>nul && echo FFmpeg: OK || (echo FFmpeg: MISSING && exit /b 1)
	@where ffprobe >nul 2>nul && echo FFprobe: OK || (echo FFprobe: MISSING && exit /b 1)
	@venv\Scripts\python.exe -m pip check

else

	@printf "\nAudiobook Library Environment\n"
	@printf "============================\n"
	@printf "OS: $(DETECTED_OS)\n"
	@printf "System Python: "; $(PYTHON) --version
	@if [ -x "$(VENV_PYTHON)" ]; then \
		printf "Venv Python:   "; $(VENV_PYTHON) --version; \
		if $(VENV_PYTHON) -m pip --version >/dev/null 2>&1; then \
			printf "Pip:           OK\n"; \
		else \
			printf "Pip:           MISSING/UNUSABLE\n"; \
			exit 1; \
		fi; \
	else \
		printf "Venv Python:   MISSING\n"; \
		exit 1; \
	fi
	@if [ -f requirements.txt ]; then printf "Requirements:   present\n"; else printf "Requirements:   MISSING\n"; exit 1; fi
	@if command -v ffmpeg >/dev/null 2>&1; then printf "FFmpeg:         OK\n"; else printf "FFmpeg:         MISSING\n"; exit 1; fi
	@if command -v ffprobe >/dev/null 2>&1; then printf "FFprobe:        OK\n"; else printf "FFprobe:        MISSING\n"; exit 1; fi
	@$(VENV_PYTHON) -m pip check
	@printf "[OK]  Environment diagnostics complete.\n"

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
# SPLIT AUDIOBOOK
# ============================================================

split:
	@$(VENV_PYTHON) /Audiobook-Library/utils/split.py "$(filter-out split,$(MAKECMDGOALS))"

%:
	@:

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