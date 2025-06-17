// @ts-check
const { test, expect } = require('@playwright/test');

// Helper function to get date-time string for inputs
function getFutureDateTime(daysInFuture, hour, minute) {
  const date = new Date();
  date.setDate(date.getDate() + daysInFuture);
  date.setHours(hour, minute, 0, 0);
  // Format: YYYY-MM-DDTHH:mm
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = date.getDate().toString().padStart(2, '0');
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

test.describe('Event Auto-Tagging', () => {
  test('should auto-generate tags when creating and updating an event', async ({ page }) => {
    // 1. Login
    await page.goto('/login');
    await page.fill('input[name="email"]', 'e2e_user@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard', { timeout: 10000 });

    // 2. Navigate to Event Creation Form
    const createEventButtonSelectors = [
        '[data-testid="create-event-button"]',
        'a:has-text("New Event")',
        'button:has-text("Create Event")'
    ];
    let createEventButton;
    for (const selector of createEventButtonSelectors) {
        createEventButton = page.locator(selector).first();
        if (await createEventButton.isVisible()) {
            break;
        }
    }
    await createEventButton.click();

    // Wait for navigation or modal display if necessary
    // For example, if it's a modal:
    // await expect(page.locator('form[data-testid="event-form"]')).toBeVisible();
    // Or if it navigates to a new page:
    await page.waitForURL('**/create', {timeout: 5000});


    // 3. Create Event with Specific Content for Tagging
    const eventTitle1 = "Strategic Planning Workshop for Q4";
    const eventDescription1 = "Session to define key objectives, roadmap, and resource allocation for the upcoming quarter. Focus on market expansion and product innovation.";
    const startTime1 = getFutureDateTime(1, 9, 0); // Tomorrow 9:00 AM
    const endTime1 = getFutureDateTime(1, 17, 0);  // Tomorrow 5:00 PM

    await page.fill('input[name="title"]', eventTitle1);
    await page.fill('textarea[name="description"]', eventDescription1);
    await page.fill('input[name="start_time"]', startTime1);
    await page.fill('input[name="end_time"]', endTime1);
    // Fill other mandatory fields if any, e.g., page.fill('input[name="location"]', 'Conference Room A');

    await page.click('button[type="submit"]:has-text("Create Event"), button:has-text("Save")');

    // 4. Verify Auto-Generated Tags on Created Event
    // Wait for event creation and redirect/update. Timeout for Gemini.
    await page.waitForURL(/\/(dashboard|calendar|event\/.*)/, { timeout: 15000 });

    // Find the event. This might be tricky. If redirected to event details page:
    // Or find it in a list on dashboard/calendar.
    // For now, assume we are on a page where the event is visible or we can navigate to it.
    // Let's try to find an element that contains the event title first.
    const eventDisplay = page.locator(`*:has-text("${eventTitle1}")`).last();
    await expect(eventDisplay).toBeVisible({ timeout: 10000 });

    // Selectors for tags - adjust based on actual HTML structure
    const tagContainer = eventDisplay.locator('[data-testid="event-tags"], .event-tags, .tags').first();

    // Wait for tags to be potentially loaded
    await tagContainer.waitFor({ state: 'attached', timeout: 10000 });

    const expectedTags1 = ["planning", "strategy", "work", "q4", "workshop", "business"];
    for (const tag of expectedTags1) {
      // Check if at least a few of these tags are present
      // Using a softer check: expect any matching tag to be visible.
      await expect(tagContainer.locator(`:textMatches("${tag}", "i")`).first()).toBeVisible({ timeout: 5000 });
    }

    // 5. (Optional but Recommended) Update Event and Verify Tag Update
    // Find and click an "Edit" button for the event.
    // This selector assumes the edit button is near the event display found earlier.
    const editButton = eventDisplay.locator('button:has-text("Edit"), a:has-text("Edit")').first();
    if (!await editButton.isVisible()){
        // If not directly within eventDisplay, try a more global search if on event details page
        await page.locator(`[aria-label*="Edit ${eventTitle1}"], button:has-text("Edit Event")`).first().click();
    } else {
        await editButton.click();
    }

    await page.waitForURL('**/edit', {timeout: 5000}); // Wait for edit page/modal

    const eventTitle2 = "Urgent Client Support Call for Alpha Project";
    const eventDescription2 = "Addressing critical bug reported by major client on Alpha project. Need immediate resolution.";

    await page.fill('input[name="title"]', eventTitle2, { force: true }); // Use force if needed
    await page.fill('textarea[name="description"]', eventDescription2, { force: true });
    // Keep same time or update if necessary for the test logic

    await page.click('button[type="submit"]:has-text("Save Changes"), button:has-text("Update Event"), button:has-text("Save")');

    // Verify tags update
    await page.waitForURL(/\/(dashboard|calendar|event\/.*)/, { timeout: 15000 }); // Wait for update & redirect

    const updatedEventDisplay = page.locator(`*:has-text("${eventTitle2}")`).last();
    await expect(updatedEventDisplay).toBeVisible({ timeout: 10000 });

    const updatedTagContainer = updatedEventDisplay.locator('[data-testid="event-tags"], .event-tags, .tags').first();
    await updatedTagContainer.waitFor({ state: 'attached', timeout: 10000 });

    const expectedTags2 = ["support", "client", "urgent", "bug", "alpha", "issue"];
    for (const tag of expectedTags2) {
      await expect(updatedTagContainer.locator(`:textMatches("${tag}", "i")`).first()).toBeVisible({ timeout: 5000 });
    }

    // Optionally, check that old tags are gone (this can be flaky depending on Gemini's logic)
    const oldTagsToCheck = ["planning", "workshop"];
    for (const oldTag of oldTagsToCheck) {
        await expect(updatedTagContainer.locator(`:textMatches("${oldTag}", "i")`)).not.toBeVisible({timeout: 2000});
    }
  });
});
