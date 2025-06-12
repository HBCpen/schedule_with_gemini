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
- **Recurring Events:** Settings for daily, weekly, monthly, yearly repetitions.
- **Search:** Keyword, period, and tag-based event search.
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
