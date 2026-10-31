import AxeBuilder from '@axe-core/playwright';
import { test, expect, openWorkspace, overview } from './fixtures';
import type { Browser, Locator, Page, TestInfo } from '@playwright/test';

async function textPreference(page: Page, info: TestInfo) {
  if (info.project.metadata.textPreference) {
    // A larger root-font preference, not a claim of native browser zoom.
    await page.addStyleTag({ content: ':root { font-size: 200%; }' });
    expect(await page.evaluate(() => getComputedStyle(document.body).fontSize)).toBe('32px');
  }
}

async function inspect(page: Page, browser: Browser, info: TestInfo, name: string) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const overlaps = await page.locator('.sidebar').evaluate(sidebar => {
    const boxes = Array.from(sidebar.querySelectorAll('.brand, .nav-name, .nav-icon')).map(element => {
      const box = element.matches('svg') ? element.getBoundingClientRect() : (() => {
        const range = document.createRange(); range.selectNodeContents(element); return range.getBoundingClientRect();
      })();
      return { name: element.getAttribute('aria-label') ?? element.textContent?.trim() ?? 'navigation icon',
        left: box.left, right: box.right, top: box.top, bottom: box.bottom };
    });
    return boxes.flatMap((box, index) => boxes.slice(index + 1).filter(other =>
      Math.min(box.right, other.right) - Math.max(box.left, other.left) > 1 &&
      Math.min(box.bottom, other.bottom) - Math.max(box.top, other.top) > 1
    ).map(other => [box.name, other.name]));
  });
  expect(overlaps, 'Navigation text and icons must remain distinct when text grows').toEqual([]);
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  await info.attach(`${name}-axe`, { body: JSON.stringify(result, null, 2), contentType: 'application/json' });
  expect(result.violations.map(item => ({ rule: item.id, targets: item.nodes.map(node => node.target) }))).toEqual([]);
  await info.attach(`${name}-environment`, { body: JSON.stringify({
    project: info.project.name, browser: browser.browserType().name(), version: browser.version(),
    viewport: page.viewportSize(), textPreference: !!info.project.metadata.textPreference,
    nativeZoomVerified: false, screenReaderVerified: false,
  }), contentType: 'application/json' });
  await page.screenshot({ path: info.outputPath(`${name}.png`), fullPage: true });
}

async function focusInView(page: Page, control: Locator) {
  await expect(control).toBeFocused();
  const box = await control.boundingBox();
  expect(box).not.toBeNull();
  const viewport = page.viewportSize()!;
  expect(box!.x).toBeGreaterThanOrEqual(-1);
  expect(box!.y).toBeGreaterThanOrEqual(-1);
  expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width + 1);
  expect(box!.y + box!.height).toBeLessThanOrEqual(viewport.height + 1);
}

async function tabTo(page: Page, control: Locator, tabKey: string) {
  const traversal: unknown[] = [];
  for (let step = 0; step < 80; step++) {
    await page.keyboard.press(tabKey);
    traversal.push(await page.evaluate(() => {
      const active = document.activeElement;
      return { tag: active?.tagName, id: active?.id, name: active?.getAttribute('aria-label'),
        text: active?.textContent?.trim().slice(0, 100), scrollY };
    }));
    if (await control.evaluate(element => element === document.activeElement)) {
      await focusInView(page, control);
      return;
    }
  }
  await test.info().attach('failed-keyboard-traversal', {
    body: JSON.stringify(traversal, null, 2), contentType: 'application/json',
  });
  throw new Error(`Keyboard could not reach ${await control.getAttribute('aria-label') ?? await control.textContent()}`);
}

for (const screen of ['Plan', 'Purchases', 'Timeline']) {
  test(`${screen}: reviewed responsive layout and accessibility`, async ({ page, scenario, browser }, info) => {
    await openWorkspace(page, scenario);
    await textPreference(page, info);
    await page.getByRole('navigation', { name: 'Workspace' }).getByRole('button', { name: screen === 'Plan' ? 'Budget and plan' : screen, exact: true }).click();
    await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1);
    await inspect(page, browser, info, screen.toLowerCase());
  });
}

test('keyboard reviews a plan and exact cart without confirming or paying', async ({ page, scenario, browser }, info) => {
  // macOS WebKit's native Option+Tab traverses links and buttons as well as fields.
  const tabKey = browser.browserType().name() === 'webkit' && process.platform === 'darwin' ? 'Alt+Tab' : 'Tab';
  const previewRequests: unknown[] = [];
  await page.route('**/v1/plan/preview', async route => {
    const body = route.request().postDataJSON();
    previewRequests.push(body);
    await route.fulfill({ json: { spec: body.plan, mode: body.mode, summary: overview('ready').plan,
      preview_hash: 'synthetic-reviewed-plan', activation_blocked_by: null, releases_purchase_ids: [] } });
  });
  await openWorkspace(page, scenario);
  await textPreference(page, info);
  await page.keyboard.press(tabKey);
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('main')).toBeFocused();
  await tabTo(page, page.getByLabel('Current cash (USD)', { exact: true }), tabKey);
  const bills = page.locator('summary').filter({ hasText: 'Bills to protect' });
  await tabTo(page, bills, tabKey);
  await page.keyboard.press('Enter');
  await tabTo(page, page.getByLabel('Bill 1 name', { exact: true }), tabKey);
  await expect(page.getByLabel('Bill 1 name', { exact: true })).toHaveValue('Demo utilities');
  await tabTo(page, page.getByRole('button', { name: 'Preview protections' }), tabKey);
  await page.keyboard.press('Enter');
  await expect(page.getByRole('heading', { name: 'Review your protections' })).toBeVisible();
  await tabTo(page, page.getByRole('button', { name: 'Confirm this plan' }), tabKey);
  expect(previewRequests).toHaveLength(1);
  await inspect(page, browser, info, 'plan-review');
  await tabTo(page, page.getByRole('button', { name: 'Purchases', exact: true }), tabKey);
  await page.keyboard.press('Enter');
  const consent = page.getByRole('checkbox', { name: 'I approve these exact items and the $100.00 total.' });
  await tabTo(page, consent, tabKey);
  await page.keyboard.press('Space');
  await expect(consent).toBeChecked();
  const approve = page.getByRole('button', { name: 'Approve exact cart' });
  await page.keyboard.press(tabKey);
  await focusInView(page, approve);
  await expect(approve).toBeEnabled();
  // Leave approval and financial mutations to the owner; fixtures reject them.
  await tabTo(page, page.getByRole('button', { name: 'Timeline', exact: true }), tabKey);
  await page.keyboard.press('Enter');
  await tabTo(page, page.getByRole('button', { name: 'Refresh workspace' }), tabKey);
  await page.keyboard.press('Enter');
  await expect(page.getByRole('list', { name: 'Recorded events' })).toBeVisible();
});

test.describe('uncertain payment review', () => {
  test.use({ scenario: 'uncertain' });
  test('retains the commitment and exposes only deliberate status refresh', async ({ page, scenario, browser }, info) => {
    await openWorkspace(page, scenario);
    await textPreference(page, info);
    await page.getByRole('button', { name: 'Purchases', exact: true }).click();
    await expect(page.getByText(/Budget remains committed/)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Capture after manual fulfilment' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Approve exact cart' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Refresh payment status' })).toBeVisible();
    await inspect(page, browser, info, 'uncertain-payment');
  });
});
