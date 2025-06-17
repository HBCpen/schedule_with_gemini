// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Natural Language Event Creation', () => {
  test('should allow users to log in, create an event using natural language, and see it on the dashboard', async ({ page }) => {
    // 1. Login
    await page.goto('/login');
    await page.fill('input[name="email"]', 'e2e_user@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');

    // Verify successful login by checking for redirection to dashboard or presence of logout
    // Using a longer timeout as the login might involve backend user creation on first try
    await expect(page).toHaveURL('/dashboard', { timeout: 10000 });
    // Or, alternatively, check for a logout button if the URL doesn't change or is less reliable
    // await expect(page.getByRole('button', { name: 'Logout' })).toBeVisible({ timeout: 10000 });

    // 2. Navigate to Natural Language Event Input
    // Try a few common selectors for the NLP input/button
    const nlpInputSelectors = [
      '[data-testid="nlp-event-input"]',
      'textarea[placeholder*="Describe your event"]',
      'button:has-text("Add with AI")',
      'button:has-text("Create Event with AI")'
    ];

    let nlpElement;
    for (const selector of nlpInputSelectors) {
      nlpElement = page.locator(selector);
      if (await nlpElement.isVisible()) {
        break;
      }
    }

    if (!nlpElement || !(await nlpElement.isVisible())) {
      // If no direct input/button, maybe it's a general "Create Event" button that leads to a page with the option
      await page.getByRole('button', { name: 'Create Event' }).first().click();
      // Then look for the NLP input again on the new page/modal
      for (const selector of nlpInputSelectors) {
        nlpElement = page.locator(selector);
        if (await nlpElement.isVisible()) {
          break;
        }
      }
    }

    await expect(nlpElement).toBeVisible();

    const nlpQuery = "Team meeting next Tuesday at 10am for 1 hour about project Phoenix";

    if (await nlpElement.getByRole('button').count() > 0) { // It's a button that likely opens a modal
      await nlpElement.click();
      // Now find the actual input field within the modal/dialog
      const modalInput = page.locator('textarea[placeholder*="Describe your event"], [data-testid="nlp-modal-input"]');
      await modalInput.fill(nlpQuery);
      await page.getByRole('button', { name: 'Parse Event' }).click(); // Assuming a parse button
    } else { // It's a direct input field
      await nlpElement.fill(nlpQuery);
      // Check if there's a button to explicitly parse or if it auto-parses
      const parseButton = page.getByRole('button', { name: 'Parse' });
      if (await parseButton.isVisible()) {
        await parseButton.click();
      }
      // Add a small delay for auto-parsing if no explicit button
      await page.waitForTimeout(1000);
    }

    // 4. Verify Form Pre-fill
    // Wait for fields to be populated, increasing timeout for Gemini API call
    await page.waitForSelector('input[name="title"][value*="Team meeting"]', { timeout: 15000 });

    const titleInput = page.locator('input[name="title"]');
    await expect(titleInput).toHaveValue(/Team meeting|project Phoenix/i);

    // Date for "next Tuesday" - this is tricky.
    // For now, we'll check if the date input has *any* value, assuming Gemini filled it.
    // A more robust test would calculate the expected date.
    const dateInput = page.locator('input[name="start_time"]'); // Assuming datetime-local
    await expect(dateInput).not.toHaveValue('');

    // Time: "10:00 AM"
    // For datetime-local input, the value would be like "YYYY-MM-DDTHH:mm"
    await expect(dateInput).toHaveValue(/T10:00|T10:00:00/);


    // Duration/End Time: 1 hour later (11:00 AM)
    const endTimeInput = page.locator('input[name="end_time"]');
    await expect(endTimeInput).not.toHaveValue('');
    await expect(endTimeInput).toHaveValue(/T11:00|T11:00:00/);

    const descriptionInput = page.locator('textarea[name="description"]');
    await expect(descriptionInput).toHaveValue(/project Phoenix/i);

    // 5. Submit Event Form
    const createButtonSelectors = [
        'button[type="submit"]:has-text("Create Event")',
        'button:has-text("Save Event")',
        'button:has-text("Save")'
    ];
    let createButton;
    for (const selector of createButtonSelectors) {
        createButton = page.locator(selector);
        if (await createButton.isVisible()){
            break;
        }
    }
    await createButton.click();

    // 6. Verify Event Creation
    // Check for redirection or confirmation message, then look for the event.
    // This might redirect back to /dashboard or a /calendar page.
    // Add a longer timeout for event processing and UI update.
    await page.waitForURL(/\/(dashboard|calendar)/, { timeout: 10000 });

    const eventDisplaySelectors = [
      'div.event-title:has-text("Team meeting")',
      '[data-testid="event-item"]:has-text("Team meeting")',
      'text=/Team meeting.*project Phoenix/' // More general text search
    ];

    let eventDisplay;
    for (const selector of eventDisplaySelectors){
        eventDisplay = page.locator(selector).first(); // Take the first match if multiple
        if(await eventDisplay.isVisible({timeout: 5000})) { // Short timeout to quickly check visibility
            break;
        }
    }
    await expect(eventDisplay).toBeVisible({ timeout: 10000 }); // Final assertion with longer timeout
    await expect(eventDisplay).toHaveText(/project Phoenix/i);

  });
});

// Helper function to calculate next Tuesday (optional, if needed for more precise date checks)
// function getNextTuesdayISO() {
//   const today = new Date();
//   const dayOfWeek = today.getDay(); // Sunday = 0, Monday = 1, ..., Saturday = 6
//   const daysUntilTuesday = (2 - dayOfWeek + 7) % 7;
//   const nextTuesday = new Date(today);
//   nextTuesday.setDate(today.getDate() + (daysUntilTuesday === 0 ? 7 : daysUntilTuesday)); // if today is Tuesday, get next week's Tuesday
//   return nextTuesday.toISOString().split('T')[0]; // Returns YYYY-MM-DD
// }
