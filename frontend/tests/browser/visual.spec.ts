import { test, expect, openWorkspace } from './fixtures';
import type { Scenario } from './fixtures';

for (const screen of ['Plan', 'Purchases', 'Timeline']) {
  test(`${screen}: synthetic ready screen`, async ({ page, scenario }) => {
    await openWorkspace(page, scenario);
    await page.getByRole('navigation', { name: 'Workspace' }).getByRole('button', { name: screen === 'Plan' ? 'Budget and plan' : screen }).click();
    await expect(page).toHaveScreenshot(`${screen.toLowerCase()}-ready.png`, { fullPage: true });
  });
}
for (const state of ['empty', 'loading', 'error', 'offline', 'locked', 'uncertain'] as Scenario[]) {
  test.describe(state, () => {
    test.use({ scenario: state });
    test('synthetic state screenshot', async ({ page, scenario }) => {
      await openWorkspace(page, scenario);
      if (scenario === 'uncertain') await page.getByRole('button', { name: 'Purchases' }).click();
      await expect(page).toHaveScreenshot(`${scenario}.png`, { fullPage: true });
    });
  });
}
