import { test, expect } from '@playwright/test';
import { createHash } from 'node:crypto';
import { readdir, readFile, lstat } from 'node:fs/promises';
import path from 'node:path';

const sourceRoot = process.env.DOKA_E2E_SOURCE_DIR;
const username = process.env.DOKA_E2E_USERNAME || 'admin';
const password = process.env.DOKA_E2E_PASSWORD;
const importTimeout = Number(process.env.DOKA_E2E_IMPORT_TIMEOUT_MS || 90_000);
const scanTimeout = Number(process.env.DOKA_E2E_SCAN_TIMEOUT_MS || 30_000);
const understandTimeout = Number(process.env.DOKA_E2E_UNDERSTAND_TIMEOUT_MS || 60_000);
const planTimeout = Number(process.env.DOKA_E2E_PLAN_TIMEOUT_MS || 30_000);

test.beforeAll(async () => {
  if (!sourceRoot) throw new Error('DOKA_E2E_SOURCE_DIR must point to a copied acceptance dataset.');
  if (!password) throw new Error('DOKA_E2E_PASSWORD must be provided; no password is committed to the test.');
});

async function snapshot(root: string): Promise<Record<string, string>> {
  const rootInfo = await lstat(root);
  if (rootInfo.isSymbolicLink() || !rootInfo.isDirectory()) {
    throw new Error('Acceptance source root must be a real directory, not a symbolic link.');
  }
  const output: Record<string, string> = {};
  async function walk(current: string) {
    for (const entry of await readdir(current, { withFileTypes: true })) {
      const full = path.join(current, entry.name);
      const relative = path.relative(root, full).split(path.sep).join('/');
      const info = await lstat(full);
      if (info.isSymbolicLink()) throw new Error(`Acceptance source contains a symbolic link: ${relative}`);
      if (info.isDirectory()) await walk(full);
      else if (info.isFile()) output[relative] = createHash('sha256').update(await readFile(full)).digest('hex');
    }
  }
  await walk(root);
  return output;
}

test('Personal Local browser acceptance: login → import → scan → understand → review plan', async ({ page }) => {
  test.setTimeout(Number(process.env.DOKA_E2E_TEST_TIMEOUT_MS || 120_000));
  const before = await snapshot(sourceRoot!);
  const sourceFileCount = Object.keys(before).length;
  expect(sourceFileCount).toBeGreaterThan(0);

  await page.goto('/login');
  await expect(page.getByTestId('login-username')).toBeVisible();
  await page.getByTestId('login-username').fill(username);
  await page.getByTestId('login-password').fill(`${password!}-invalid`);
  await page.getByTestId('login-submit').click();
  await expect(page.getByRole('alert')).toHaveText('Invalid username or password.');

  await page.getByTestId('login-password').fill(password!);
  await page.getByTestId('login-submit').click();

  await page.waitForURL('**/admin/workspace');
  await expect(page.getByRole('heading', { name: 'Safe Workspace' })).toBeVisible();
  await expect(page.getByTestId('start-safe-import')).toBeEnabled();

  await page.getByTestId('start-safe-import').click();
  await expect(page.getByText(/Import started\. The original source is not modified\./)).toBeVisible();
  await expect(page.getByText('Status:')).toContainText('completed', { timeout: importTimeout });
  await expect(page.getByText(/Verified:/)).toContainText(
    new RegExp(`${sourceFileCount}\\s*/\\s*${sourceFileCount}`),
  );
  await expect(page.getByText(/Failed:/)).toHaveText(/Failed:\s*0/);

  await page.getByTestId('scan-copy').click();
  await expect(page.getByText('scan completed.')).toBeVisible({ timeout: scanTimeout });

  const understandingResponsePromise = page.waitForResponse((response) =>
    response.url().includes('/understanding') && response.request().method() === 'GET',
  );
  await page.getByTestId('run-ocr').click();
  await expect(page.getByText('understand completed.')).toBeVisible({ timeout: understandTimeout });
  const understandingResponse = await understandingResponsePromise;
  expect(understandingResponse.ok()).toBeTruthy();
  const understanding = await understandingResponse.json() as {
    analyzed_files?: number;
    results?: Array<{ extension?: string; text_length?: number; extraction_method?: string }>;
  };
  expect(understanding.analyzed_files).toBe(sourceFileCount);
  expect(understanding.results).toHaveLength(sourceFileCount);
  const ocrExtensions = new Set(['.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp']);
  const ocrResults = understanding.results?.filter((result) =>
    ocrExtensions.has((result.extension || '').toLowerCase()),
  ) || [];
  const emptyOcrCount = ocrResults.filter((result) =>
    result.extraction_method === 'ocr_failed' || !result.text_length,
  ).length;
  expect(emptyOcrCount).toBe(0);

  await page.getByTestId('build-review-plan').click();
  await expect(page.getByText('plan completed.')).toBeVisible({ timeout: planTimeout });

  await page.reload();
  await expect(page).toHaveURL(/\/admin\/workspace$/);
  await expect(page.getByRole('heading', { name: 'Safe Workspace' })).toBeVisible();

  const after = await snapshot(sourceRoot!);
  expect(after).toEqual(before);
});
