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

test.describe('Related Information Display for Events', () => {
  test('should display weather, traffic, and other related info for an event with location', async ({ page }) => {
    // 1. Login
    await page.goto('/login');
    await page.fill('input[name="email"]', 'e2e_user@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard', { timeout: 10000 });

    // 2. Create an Event with Location and Future Date
    await page.getByRole('button', { name: /Create Event|New Event/i }).first().click();
    // Wait for navigation or modal display
    await page.waitForURL('**/create', {timeout: 5000}); // Or specific modal selector

    const eventTitle = "Conference Trip to San Francisco";
    const eventLocation = "Moscone Center, San Francisco, CA";
    const startTime = getFutureDateTime(3, 10, 0); // 3 days in future, 10:00 AM
    const endTime = getFutureDateTime(3, 18, 0);   // 3 days in future, 6:00 PM

    await page.fill('input[name="title"]', eventTitle);
    await page.fill('textarea[name="description"]', "Attending the Global Tech Summit.");
    await page.fill('input[name="location"]', eventLocation);
    await page.fill('input[name="start_time"]', startTime);
    await page.fill('input[name="end_time"]', endTime);

    await page.click('button[type="submit"]:has-text("Create Event"), button:has-text("Save")');

    // After creation, navigate/ensure view of this specific event's detail.
    // This might redirect to a details page, or require clicking on the event in a calendar/list.
    // Assuming redirection or the event is immediately visible and clickable.
    // Increased timeout for event processing and potential Gemini calls on creation (e.g. auto-tagging)
    await page.waitForURL(/\/(dashboard|calendar|event\/.*)/, { timeout: 15000 });

    let eventLink;
    // Try to find the event in a list or calendar view to click on it for details
    // This is a common pattern if not redirected to details page directly.
    const eventInListSelector = `[data-testid="event-item"]:has-text("${eventTitle}"), div.event:has-text("${eventTitle}")`;

    eventLink = page.locator(eventInListSelector).first();
    if (await eventLink.isVisible()) {
        await eventLink.click();
        // Wait for navigation to the event detail page
        await page.waitForURL(/event\/[a-zA-Z0-9]+/, { timeout: 10000 }); // Regex for typical event ID URL
    } else {
        // If not found in a list, assume we might already be on a page that will show details,
        // or the details are part of a master-detail view.
        // We will proceed to check for detail sections.
        // If it's a single page app that updates content, ensure the URL is what's expected for an event view
        // or a specific element marking the event detail view is present.
        await expect(page.locator(`h1:has-text("${eventTitle}"), h2:has-text("${eventTitle}")`)).toBeVisible({timeout:10000});
    }


    // 3. Verify Related Information Display
    // Wait for these sections to load; they might depend on async calls to Gemini.
    // Using longer timeouts for these sections.

    // Weather Forecast
    const weatherInfo = page.locator('[data-testid="weather-info"], .weather-details, #weather-forecast');
    await expect(weatherInfo).toBeVisible({ timeout: 20000 });
    await expect(weatherInfo.locator('p, div').first()).not.toBeEmpty({ timeout: 5000 }); // Check it has some content

    // Traffic Information
    const trafficInfo = page.locator('[data-testid="traffic-info"], .traffic-details, #traffic-conditions');
    await expect(trafficInfo).toBeVisible({ timeout: 20000 });
    await expect(trafficInfo.locator('p, div').first()).not.toBeEmpty({ timeout: 5000 });

    // Suggestions (e.g., restaurants, points of interest)
    const suggestionsInfo = page.locator('[data-testid="suggestions-info"], .suggestions-list, #poi-suggestions');
    await expect(suggestionsInfo).toBeVisible({ timeout: 20000 });
    // This section might be empty if no suggestions, but the container should exist.
    // Optionally, check for child elements if suggestions are expected:
    // await expect(suggestionsInfo.locator('.suggestion-item').first()).toBeVisible({ timeout: 5000 });

    // Related Content (e.g., news, documents)
    const relatedContentInfo = page.locator('[data-testid="related-content-info"], .related-articles, #related-news');
    await expect(relatedContentInfo).toBeVisible({ timeout: 20000 });
    // This section might also be empty, but the container should exist.
    // Optionally, check for child elements:
    // await expect(relatedContentInfo.locator('.article-link').first()).toBeVisible({ timeout: 5000 });


    // A more robust check for sections with potentially empty content is to ensure the section header or container exists.
    // For example, if each section has a heading:
    await expect(page.locator('h3:has-text("Weather")')).toBeVisible({timeout: 1000});
    await expect(page.locator('h3:has-text("Traffic")')).toBeVisible({timeout: 1000});
    await expect(page.locator('h3:has-text("Suggestions")')).toBeVisible({timeout: 1000});
    // await expect(page.locator('h3:has-text("Related Content")')).toBeVisible({timeout: 1000}); // if "Related Content" is a heading

    // Verify some text content within each, ensuring they are not just empty containers
    expect(await weatherInfo.innerText()).not.toBe('');
    expect(await trafficInfo.innerText()).not.toBe('');
    // For suggestions and related content, they might be legitimately empty,
    // so checking innerText might be too strict if no items are found.
    // The .toBeVisible check for the container itself is the main assertion for these.
  });
});
