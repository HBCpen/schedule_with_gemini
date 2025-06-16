# Environment Setup Issues and Resolutions

This document outlines specific dependency issues encountered during the setup and testing of the `gemini_scheduler_app` backend and frontend components, along with the resolutions or workarounds applied.

## Backend Dependencies (`gemini_scheduler_app/backend/requirements.txt`)

Several packages in `requirements.txt` caused installation failures in the provided environment. System-level dependencies were missing, and some Python package builds also seemed to require Python development headers.

1.  **`PyGObject`**:
    *   **Issue**: Installation failed, requiring `pkg-config` and `libcairo2-dev` system packages. Even after installing these, further build issues occurred, possibly related to missing Python C headers/development files.
    *   **Attempted System Fixes**: `sudo apt-get install -y pkg-config libcairo2-dev python3-dev`
    *   **Workaround**: Due to persistent issues and since `PyGObject` (used for GUI features, often via GTK) was deemed non-critical for the backend API and its unit tests, it was commented out in `requirements.txt`.

2.  **`dbus-python`**:
    *   **Issue**: Installation failed, requiring the `libdbus-1-dev` system package. Similar to `PyGObject`, build issues persisted even after installing the system dependency, potentially due to Python C header issues.
    *   **Attempted System Fixes**: `sudo apt-get install -y libdbus-1-dev python3-dev`
    *   **Workaround**: As `dbus-python` (for D-Bus system messaging) was not essential for the core backend API functionality being tested, it was commented out in `requirements.txt`.

3.  **`tox`**:
    *   **Issue**: Caused a version conflict with `cachetools`. `tox` required `cachetools>=5.5.1`, while `google-auth` (a transitive dependency) required `cachetools==5.5.0`.
    *   **Workaround**: `tox` is a tool for automating test environments. Since tests were being run directly with `pytest`, `tox` was not strictly necessary for the immediate goal of executing backend unit tests. It was commented out in `requirements.txt` to resolve the conflict.

**Note on Python Development Headers**: While `python3-dev` was installed to provide C headers, some packages might have more specific build system requirements or look for these headers in non-standard paths if the Python environment is not set up in a particular way (e.g., virtual environment vs. system Python).

## Frontend Dependencies (`gemini_scheduler_app/frontend/package.json`)

1.  **`react-router-dom` (and `react-router`)**:
    *   **Issue**: `npm install` initially showed `EBADENGINE` warnings because `react-router-dom@7.6.2` (and its dependency `react-router@7.6.2`) requires Node.js version `^20.0.0` or `>=20.0.0`. The testing environment initially had Node.js v18.x. This led to `Cannot find module 'react-router-dom'` errors when running Jest tests for `src/App.test.js`.
    *   **Solution**: Node.js was upgraded in the environment.
        *   The `n` Node version manager was installed globally: `sudo npm install -g n`
        *   Node.js v20 (LTS) was installed and activated: `sudo n 20 --yes` (the `--yes` flag was assumed to work non-interactively; `n lts` or `n 20.x.x` would also work).
        *   The `PATH` environment variable was updated to ensure the new Node.js version was used: `export PATH="/usr/local/bin:$PATH"`.
        *   `node_modules` and `package-lock.json` were removed, and `npm install` was re-run. This successfully installed `react-router-dom` without `EBADENGINE` errors, and subsequent Jest tests (after further Jest-specific module resolution fixes for `App.test.js` using manual mocks) were able to find the module.

**Summary of Critical System Packages Installed for Backend (Attempted):**
*   `pkg-config`
*   `libcairo2-dev`
*   `libdbus-1-dev`
*   `python3-dev`

**Summary of Node.js Version Management for Frontend:**
*   `npm install -g n`
*   `n 20` (or a specific v20.x.x)
*   Ensuring `/usr/local/bin` is in `PATH` for the new Node version.
