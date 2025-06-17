// @ts-check
const { test, expect } = require('@playwright/test');

// Helper function to get date-time string for inputs
function getFutureDateTime(daysInFuture, hour, minute, dayOffset = 0) {
  const date = new Date();
  date.setDate(date.getDate() + daysInFuture + dayOffset);
  date.setHours(hour, minute, 0, 0);
  // Format: YYYY-MM-DDTHH:mm
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = date.getDate().toString().padStart(2, '0');
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

test.describe('Subtask Suggestion Functionality', () => {
  test('should suggest subtasks for a complex event', async ({ page }) => {
    // 1. Login
    await page.goto('/login');
    await page.fill('input[name="email"]', 'e2e_user@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard', { timeout: 10000 });

    // 2. Create a Complex Event
    await page.getByRole('button', { name: /Create Event|New Event/i }).first().click();
    await page.waitForURL('**/create', {timeout: 5000});

    const eventTitle = "Organize Annual Company Offsite Meeting";
    const eventDescription = "Plan and execute the full 2-day offsite event for 75 employees. This includes finding a venue, arranging catering, planning team-building activities, coordinating travel, and managing the budget.";
    const startTime = getFutureDateTime(14, 9, 0); // 2 weeks from now, 9:00 AM
    const endTime = getFutureDateTime(14, 17, 0, 2); // 2 weeks + 2 days from now, 5:00 PM

    await page.fill('input[name="title"]', eventTitle);
    await page.fill('textarea[name="description"]', eventDescription);
    await page.fill('input[name="start_time"]', startTime);
    await page.fill('input[name="end_time"]', endTime);
    // Add location if mandatory, e.g. page.fill('input[name="location"]', 'TBD');


    await page.click('button[type="submit"]:has-text("Create Event"), button:has-text("Save")');

    // Ensure navigation to or identification of the created event's detail view.
    await page.waitForURL(/\/(dashboard|calendar|event\/.*)/, { timeout: 15000 });

    let eventLinkOrDetailView = page.locator(`h1:has-text("${eventTitle}"), h2:has-text("${eventTitle}")`);
    if (!await eventLinkOrDetailView.isVisible()) {
        const eventInListSelector = `[data-testid="event-item"]:has-text("${eventTitle}"), div.event:has-text("${eventTitle}")`;
        const eventLink = page.locator(eventInListSelector).first();
        await expect(eventLink).toBeVisible({ timeout: 10000 });
        await eventLink.click();
        await page.waitForURL(/event\/[a-zA-Z0-9]+/, { timeout: 10000 });
        await expect(page.locator(`h1:has-text("${eventTitle}"), h2:has-text("${eventTitle}")`)).toBeVisible({timeout:10000});
    } else {
        await expect(eventLinkOrDetailView).toBeVisible({timeout:10000});
    }


    // 3. Trigger Subtask Suggestion
    const suggestButtonSelectors = [
      '[data-testid="suggest-subtasks-button"]',
      'button:has-text("Suggest Subtasks")',
      'button:has-text("Breakdown Task")',
      'button:has-text("Generate Subtasks")'
    ];

    let suggestButton;
    for(const selector of suggestButtonSelectors) {
        suggestButton = page.locator(selector);
        if (await suggestButton.isVisible()) {
            break;
        }
    }
    await expect(suggestButton).toBeVisible({ timeout: 10000 });
    await suggestButton.click();

    // 4. Verify Subtask List Display
    // Wait for the subtask suggestions to load (these come from Gemini).
    const subtaskContainer = page.locator('[data-testid="subtasks-list-container"], .subtasks-section, #suggested-subtasks');
    await expect(subtaskContainer).toBeVisible({ timeout: 20000 }); // Increased timeout for Gemini

    const subtaskItemSelectors = [
      '[data-testid="subtask-item"]',
      '.subtask-list li',
      '.suggested-subtasks .subtask',
      '.subtask-text'
    ];

    // Check that at least a few subtasks (e.g., > 2) are displayed.
    const firstSubtask = subtaskContainer.locator(subtaskItemSelectors.join(', ')).first();
    await expect(firstSubtask).toBeVisible({ timeout: 10000 });

    const allSubtasks = await subtaskContainer.locator(subtaskItemSelectors.join(', ')).count();
    expect(allSubtasks).toBeGreaterThan(2);

    // Verify that they contain some text (not empty).
    const subtaskTexts = await subtaskContainer.locator(subtaskItemSelectors.join(', ')).allTextContents();
    for (const text of subtaskTexts) {
      expect(text.trim()).not.toBe('');
      // console.log(`Suggested Subtask: ${text.trim()}`);
    }

    // Example: Check if one of the common subtasks is present
    const commonSubtaskText = /venue|catering|activities|travel|budget/i;
    const matchingSubtask = subtaskContainer.locator(`:text-matches("${commonSubtaskText.source}", "i")`).first();
    await expect(matchingSubtask).toBeVisible({timeout: 5000});

  });
});
