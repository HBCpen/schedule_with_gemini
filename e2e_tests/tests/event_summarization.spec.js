// @ts-check
const { test, expect } = require('@playwright/test');

// Helper function to get date-time string for inputs
function getFutureDateTime(daysInFuture, hour, minute) {
  const date = new Date();
  date.setDate(date.getDate() + daysInFuture);
  date.setHours(hour, minute, 0, 0);
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = date.getDate().toString().padStart(2, '0');
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

// Helper function to get just the date part in YYYY-MM-DD format
function getFutureDate(daysInFuture) {
  const date = new Date();
  date.setDate(date.getDate() + daysInFuture);
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = date.getDate().toString().padStart(2, '0');
  return `${year}-${month}-${day}`;
}

test.describe('Event Summarization Functionality', () => {
  const summaryDayOffset = 5; // 5 days in the future
  const summaryDate = getFutureDate(summaryDayOffset);
  const summaryDateTime1Start = getFutureDateTime(summaryDayOffset, 9, 0);
  const summaryDateTime1End = getFutureDateTime(summaryDayOffset, 11, 0);
  const event1Title = "Morning Strategy Session";
  const event1Desc = "Discuss Q4 marketing plan.";

  const summaryDateTime2Start = getFutureDateTime(summaryDayOffset, 14, 0);
  const summaryDateTime2End = getFutureDateTime(summaryDayOffset, 15, 0);
  const event2Title = "Client Demo - Project Zeta";
  const event2Desc = "Showcase new features to the client.";

  async function createEvent(page, title, description, startTime, endTime) {
    await page.getByRole('button', { name: /Create Event|New Event/i }).first().click();
    await page.waitForURL('**/create', {timeout: 5000});

    await page.fill('input[name="title"]', title);
    await page.fill('textarea[name="description"]', description);
    await page.fill('input[name="start_time"]', startTime);
    await page.fill('input[name="end_time"]', endTime);
    // Add location if mandatory, e.g. page.fill('input[name="location"]', 'Office');

    await page.click('button[type="submit"]:has-text("Create Event"), button:has-text("Save")');
    // Wait for event creation and redirect/UI update
    await page.waitForURL(/\/(dashboard|calendar)/, { timeout: 10000 });
    // Verify event appears (optional, but good for sanity)
    // await expect(page.locator(`*:has-text("${title}")`).last()).toBeVisible();
  }

  test('should generate a summary for a day with multiple events', async ({ page }) => {
    // 1. Login
    await page.goto('/login');
    await page.fill('input[name="email"]', 'e2e_user@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard', { timeout: 10000 });

    // 2. Create Multiple Events for a Specific Future Day
    await createEvent(page, event1Title, event1Desc, summaryDateTime1Start, summaryDateTime1End);
    // Navigate back to dashboard or a neutral place if createEvent doesn't leave us there
    if (!page.url().includes('/dashboard') && !page.url().includes('/calendar')) {
        await page.goto('/dashboard');
    }
    await createEvent(page, event2Title, event2Desc, summaryDateTime2Start, summaryDateTime2End);
    if (!page.url().includes('/dashboard') && !page.url().includes('/calendar')) {
        await page.goto('/dashboard');
    }

    // 3. Navigate to Event Summarization Interface
    const summaryInterfaceSelectors = [
      '[data-testid="get-summary-button"]', // A button that might trigger a modal or a dedicated page
      'input[name="summary-date"]', // A direct date input for summary
      'button:has-text("Get Daily Summary")',
      'a:has-text("Daily Digest")'
    ];

    let summaryElement;
    for (const selector of summaryInterfaceSelectors) {
      summaryElement = page.locator(selector).first();
      if (await summaryElement.isVisible()) {
        break;
      }
    }
    await expect(summaryElement).toBeVisible();

    // 4. Request Summary for the Specific Day
    if (await summaryElement.getAttribute('type') === 'date' || await summaryElement.getAttribute('name') === 'summary-date') {
      await summaryElement.fill(summaryDate);
      // Look for a submit button associated with this input
      const submitSummaryButton = page.locator('button:has-text("Generate Summary"), button[data-testid="submit-summary-date"]');
      await submitSummaryButton.click();
    } else {
      // Assumed to be a button that either summarizes "today" or opens a modal where a date can be selected.
      // For this test, we'll assume it's for a date that needs to be specified or is implicitly today.
      // If it's a general "Get Summary" button, it might require further interaction if it opens a modal.
      await summaryElement.click();

      // If a modal opens, look for a date input there
      const modalDateInput = page.locator('[data-testid="summary-modal-date-input"], input[type="date"].summary-modal-date');
      if (await modalDateInput.isVisible()){
          await modalDateInput.fill(summaryDate);
          await page.locator('button:has-text("Generate"), button[data-testid="modal-generate-summary"]').click();
      }
      // If no modal or specific date input found after click, the test might need adjustment
      // based on how the UI actually works. For now, proceed assuming summary generation is triggered.
    }

    // 5. Verify Summary Display and Content
    const summaryDisplayArea = page.locator('[data-testid="event-summary-text"], .summary-output p, #daily-summary-content');
    // Wait for Gemini to process and display the summary.
    await expect(summaryDisplayArea).toBeVisible({ timeout: 20000 });
    await expect(summaryDisplayArea).not.toBeEmpty({ timeout: 10000 });

    const summaryText = await summaryDisplayArea.innerText();
    expect(summaryText.length).toBeGreaterThan(10); // Basic check for some content

    // Verify key details from the created events (flexible matching)
    await expect(summaryDisplayArea).toContainText(event1Title, { timeout: 5000 });
    await expect(summaryDisplayArea).toContainText(/Q4 marketing/i, { timeout: 5000 });
    await expect(summaryDisplayArea).toContainText(event2Title, { timeout: 5000 });
    await expect(summaryDisplayArea).toContainText(/Project Zeta/i, { timeout: 5000 });

    // console.log("Generated Summary:", summaryText);
  });
});
