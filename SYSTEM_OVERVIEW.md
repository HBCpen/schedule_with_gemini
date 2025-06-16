## Application Purpose
This is a browser-based schedule management application designed for intuitive use. It leverages the Gemini API for advanced features, aiming to make schedule management more efficient and intelligent. Users receive email reminders for upcoming appointments.

## Key Features

### User Management
- Account creation, login, and logout (basic email/password authentication).
- Optional profile settings (name, timezone, etc.).

### Schedule Management
- **Manual Entry:** Input title, start/end times, location, detailed notes, color-coded tags.
- **Natural Language Input (via Gemini API):**
    - Example: "Meeting with Mr. A in Shibuya tomorrow at 14:00, also set a reminder for document preparation."
    - Gemini API interprets and suggests entries for date, time, location, attendees, content, and reminders.
    - Users confirm/modify suggestions before saving.
- **Event Display:**
    - Calendar formats (monthly, weekly, daily).
    - List format.
    - Gemini API-powered summary (e.g., "You have 3 important events today: a morning meeting, an afternoon client visit, and an evening deadline for document submission.").
- **Edit/Delete:** Intuitive modification and deletion of events.
- **Search:** Comprehensive search functionality allowing users to find events by keywords (in title and description), specific date ranges (period), and associated tags.
- **Recurring Events:**
    -   Allows users to define recurrence rules for events.
    -   The UI provides simple settings for "Daily" and "Weekly" (with selection of specific days) recurrence, including setting an interval (e.g., every 2 weeks) and an optional end date for the series.
    -   The backend can store any valid iCalendar RRULE string, allowing for more complex rules if set programmatically or by future UI enhancements (e.g., monthly, yearly).
    -   Recurring event instances are dynamically generated for display within the requested calendar view.
- **Sharing (Optional):** Share specific events with other users.

### Reminder Functions
- **Email Reminders:** Notifications sent N minutes/hours/days before an event's start time, configurable by the user.
- **Personalized Emails (via Gemini API):** Enhance reminder emails with information like weather forecasts or travel route suggestions.
- **Browser Notifications (Optional):** Real-time alerts using Web Push API.

### Advanced Gemini API Features
- **Automatic Tagging/Categorization:** Gemini API analyzes event content (e.g., "meeting," "dinner," "exercise") and suggests tags/categories.
- **Free Time Search/Suggestion:**
    - Natural language queries like, "What 2-hour slots are free next Monday afternoon?"
    - Gemini API analyzes the calendar and presents available times.
    - Assists in coordinating schedules for multiple participants (integrates with sharing).
- **Related Information:**
    - Based on event location, Gemini API provides weather forecasts, traffic information, nearby restaurant suggestions.
    - Suggests news articles or documents related to event content (with user permission).
- **Task Proposal/Breakdown:**
    - For large events (e.g., "New Product Proposal Writing"), Gemini API suggests necessary sub-tasks (e.g., "market research," "competitor analysis," "draft creation") and helps register them as a To-Do list.
- **Learning from Past Schedules:**
    - Analyzes past schedule patterns to suggest automatic registration of routine work or recommend productive time slots (with privacy considerations).

## Architecture

The application follows a client-server architecture:

-   **Frontend:** Developed using **React**, a modern JavaScript library for building user interfaces. It provides a component-based structure for efficient UI development.
-   **Backend:** Built with **Python** using the **Flask** framework. This choice was made for its ease of integration with the Gemini API (via the Python SDK) and its rich library support.
-   **Database:** The specific database (e.g., PostgreSQL, MySQL, MongoDB) would be chosen based on the characteristics of the schedule data (relational or document-oriented).
-   **Email Sending:** Utilizes an email delivery service (e.g., SendGrid, Mailgun, Amazon SES) or a self-hosted SMTP server for sending event reminders.
-   **Infrastructure:** Likely deployed on a cloud platform such as Google Cloud (Firebase, App Engine, Cloud Functions), AWS, or Azure to ensure scalability and access to managed services.

## Gemini API Integration

The Gemini API is a core component of this application, enabling several intelligent scheduling features. It is used for:

-   Natural language event input and parsing.
-   Generating event summaries.
-   Personalizing reminder emails with contextual information.
-   Automatic event tagging and categorization.
-   Searching for free time slots.
-   Providing related information for events (weather, traffic, suggestions).
-   Proposing and breaking down tasks for large events.
-   Learning from past schedule patterns to suggest routine entries or productive times.

### Key Considerations for Gemini API Usage
-   **API Key Management:** Securely manage and protect API keys.
-   **Usage Costs:** Understand the API call-based pricing and design for budget-conscious operation.
-   **Response Time:** Consider API response speed and use asynchronous processing where necessary to avoid impacting user experience.
-   **Error Handling:** Implement appropriate fallback measures for API errors.
-   **Privacy:** Clearly define privacy policies for sending user event data to Gemini API and obtain user consent. Handle personal information with utmost care.
-   **Prompt Engineering:** Design effective prompts to get desired results from the Gemini API.

## Development Environment Setup Guide

This guide outlines the steps to set up the development environment for both the backend and frontend components of the application.

### Backend Setup (Python/Flask)

1.  **Prerequisites:**
    *   Python 3.x installed.
    *   `pip` (Python package installer) installed.

2.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd gemini_scheduler_app/backend
    ```

3.  **Create and Activate a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

4.  **Install Dependencies:**
    Navigate to the `gemini_scheduler_app/backend` directory if you aren't already there.
    ```bash
    pip install -r requirements.txt
    ```

5.  **Configure Environment Variables:**
    - Create a `.env` file in the `gemini_scheduler_app/backend` directory.
    - Add necessary environment variables such as:
        - `FLASK_APP=app.py`
        - `FLASK_ENV=development`
        - `DATABASE_URL=<your_database_connection_string>`
        - `GEMINI_API_KEY=<your_gemini_api_key>`
        - `MAIL_SERVER=<your_mail_server>`
        - `MAIL_PORT=<your_mail_port>`
        - `MAIL_USERNAME=<your_mail_username>`
        - `MAIL_PASSWORD=<your_mail_password>`
        - `SECRET_KEY=<your_flask_secret_key>`
    *Note: Obtain actual database credentials, API keys, and mail server details as required.*

6.  **Initialize Database (If applicable):**
    *   Depending on the database and ORM used (e.g., Flask-Migrate with SQLAlchemy), you might need to run migration commands:
        ```bash
        # flask db init  (if first time)
        # flask db migrate -m "Initial migration"
        # flask db upgrade
        ```
    *Consult the specific database setup instructions if available.*

7.  **Run the Backend Development Server:**
    ```bash
    flask run
    ```
    The backend server should typically start on `http://127.0.0.1:5000/`.

### Frontend Setup (React)

1.  **Prerequisites:**
    *   Node.js (which includes npm) installed (e.g., LTS version).

2.  **Navigate to Frontend Directory:**
    ```bash
    cd gemini_scheduler_app/frontend
    ```

3.  **Install Dependencies:**
    ```bash
    npm install
    ```

4.  **Configure Environment Variables (If applicable):**
    - React apps often use `.env` files for environment variables. For example, to specify the backend API URL:
        - Create a `.env` file in the `gemini_scheduler_app/frontend` directory.
        - Add variables prefixed with `REACT_APP_`:
          ```
          REACT_APP_API_BASE_URL=http://localhost:5000/api
          ```
    *Consult the frontend code for specific environment variables used.*

5.  **Run the Frontend Development Server:**
    ```bash
    npm start
    ```
    This will usually open the application in your default web browser at `http://localhost:3000`. The page will automatically reload if you make changes to the code.

### Running Linters and Tests

-   **Backend (Example with Pytest and Flake8):**
    ```bash
    # From gemini_scheduler_app/backend
    pytest
    flake8 .
    ```
-   **Frontend (Example with ESLint and Jest/React Testing Library):**
    ```bash
    # From gemini_scheduler_app/frontend
    npm test
    npm run lint # Assuming a lint script is configured in package.json
    ```

This setup guide provides a general outline. Refer to specific READMEs or documentation within the `backend` and `frontend` directories for more detailed instructions if available.

### Known Environment Setup Issues and Resolutions

This section outlines specific dependency issues encountered during the setup and testing of the `gemini_scheduler_app` backend and frontend components, along with the resolutions or workarounds applied.

#### Backend Dependencies (`gemini_scheduler_app/backend/requirements.txt`)

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

#### Frontend Dependencies (`gemini_scheduler_app/frontend/package.json`)

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
