// @ts-check
const { test, expect } = require('@playwright/test');

test.describe('Free Time Search Functionality', () => {
  test('should allow users to search for free time slots and display suggestions', async ({ page }) => {
    // 1. Login
    await page.goto('/login');
    await page.fill('input[name="email"]', 'e2e_user@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard', { timeout: 10000 });

    // 2. Navigate to Free Time Search Interface
    // This might be directly on the dashboard or a calendar page.
    // Common selectors for the free time search input/button
    const freeTimeSearchSelectors = [
      '[data-testid="free-time-search-input"]',
      'input[placeholder*="Find free time"]',
      'input[placeholder*="Search available slots"]',
      'button:has-text("Find Free Slots")',
      'button:has-text("Search Free Time")'
    ];

    let searchElement;
    for (const selector of freeTimeSearchSelectors) {
      searchElement = page.locator(selector).first();
      if (await searchElement.isVisible()) {
        break;
      }
    }

    // If it's a button, it might open a dedicated search interface or modal
    if (await searchElement.getByRole('button').count() > 0 && !(await searchElement.getAttribute('type') === 'submit')) {
        await searchElement.click();
        // Look for an input field after clicking the button
        const modalInput = page.locator('input[placeholder*="Describe when to search"]', '[data-testid="free-time-modal-input"]');
        await expect(modalInput).toBeVisible();
        searchElement = modalInput;
    }

    await expect(searchElement).toBeVisible();

    // 3. Input Free Time Query
    const freeTimeQuery = "Show me 2-hour slots available next Wednesday afternoon";
    await searchElement.fill(freeTimeQuery);

    // 4. Trigger Search and Verify Suggestions
    // The search might be triggered by pressing Enter or clicking a search button.
    const searchButton = page.locator('button:has-text("Search"), button[aria-label*="Search"], button[data-testid="execute-free-time-search"]');
    if (await searchButton.isVisible()) {
      await searchButton.click();
    } else {
      await searchElement.press('Enter');
    }

    // Wait for results to appear (API call to backend/Gemini)
    // This selector targets a container that should hold the suggestions.
    const suggestionsContainer = page.locator(
        '[data-testid="free-slots-container"], .free-slots-list, #suggested-times'
    );
    await expect(suggestionsContainer).toBeVisible({ timeout: 20000 }); // Increased timeout for Gemini

    // Verify that at least one suggested time slot is displayed.
    const suggestedSlotSelectors = [
      '[data-testid="free-slot-item"]',
      '.suggested-slot',
      'ul.free-slots li',
      '.time-suggestion-item'
    ];

    let firstSuggestion;
    for (const selector of suggestedSlotSelectors) {
        firstSuggestion = suggestionsContainer.locator(selector).first();
        if(await firstSuggestion.isVisible({timeout: 1000})) { // Quick check
            break;
        }
    }

    await expect(firstSuggestion).toBeVisible({ timeout: 10000 }); // Assert that at least one is found

    // Further checks could involve:
    // - Verifying the number of suggestions.
    // - Checking if the suggestions roughly match "next Wednesday afternoon".
    //   This would require date parsing and comparison logic in the test, e.g.:
    //   const suggestedText = await firstSuggestion.textContent();
    //   expect(suggestedText).toMatch(/Wednesday/i);
    //   expect(suggestedText).toMatch(/PM/i); // Or check specific time ranges

    // For now, confirming that suggestions are displayed is the primary goal.
    const allSuggestions = await suggestionsContainer.locator(suggestedSlotSelectors.join(', ')).count();
    expect(allSuggestions).toBeGreaterThan(0);

    // Example: log the text of the first suggestion
    // console.log('First suggestion text:', await firstSuggestion.textContent());
  });
});

/**
 * Note on test robustness:
 * To make this test less flaky and more deterministic, consider these approaches:
 * 1.  **Seed Calendar Data**: Before running the search, programmatically create a set of events
 *     for 'e2e_user@example.com' on "next Wednesday". This gives Gemini concrete data to analyze.
 *     For example, block out the morning and late evening to force suggestions into the afternoon.
 *     This could be done via API calls if available, or UI interactions if simpler.
 *
 * 2.  **More Specific Assertions**: If the format of suggested slots is known, parse the date/time
 *     from the suggestion text/attributes and compare it against the expected "next Wednesday afternoon".
 *     Helper functions for date calculations (like getNextDayOfWeek) would be useful here.
 *
 * 3.  **Mocking API Responses**: For very stable unit-like E2E tests, the backend API call that
 *     fetches suggestions could be mocked to return a predictable set of slots. This is advanced
 *     and might deviate from true E2E testing but can be useful for UI verification.
 *
 * For the current subtask, the focus is on the primary flow: query -> search -> see some results.
 */
