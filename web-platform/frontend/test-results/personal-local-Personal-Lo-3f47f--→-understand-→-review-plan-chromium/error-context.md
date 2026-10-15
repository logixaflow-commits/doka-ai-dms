# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: personal-local.spec.ts >> Personal Local browser acceptance: login → import → scan → understand → review plan
- Location: e2e\personal-local.spec.ts:39:1

# Error details

```
Error: expect(locator).toContainText(expected) failed

Locator: getByText('Status:')
Expected substring: "completed"
Received string:    "Status: running"
Timeout: 180000ms

Call log:
  - Expect "toContainText" getByText('Status:') with timeout 180000ms
  - waiting for getByText('Status:')
    4 × locator resolved to <span>…</span>
      - unexpected value "Status: created"
    325 × locator resolved to <span>…</span>
        - unexpected value "Status: running"

```

```yaml
- text: "Status:"
- strong: running
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | import { createHash } from 'node:crypto';
  3   | import { readdir, readFile, lstat } from 'node:fs/promises';
  4   | import path from 'node:path';
  5   | 
  6   | const sourceRoot = process.env.DOKA_E2E_SOURCE_DIR;
  7   | const username = process.env.DOKA_E2E_USERNAME || 'admin';
  8   | const password = process.env.DOKA_E2E_PASSWORD;
  9   | const importTimeout = Number(process.env.DOKA_E2E_IMPORT_TIMEOUT_MS || 90_000);
  10  | const scanTimeout = Number(process.env.DOKA_E2E_SCAN_TIMEOUT_MS || 30_000);
  11  | const understandTimeout = Number(process.env.DOKA_E2E_UNDERSTAND_TIMEOUT_MS || 60_000);
  12  | const planTimeout = Number(process.env.DOKA_E2E_PLAN_TIMEOUT_MS || 30_000);
  13  | 
  14  | test.beforeAll(async () => {
  15  |   if (!sourceRoot) throw new Error('DOKA_E2E_SOURCE_DIR must point to a copied acceptance dataset.');
  16  |   if (!password) throw new Error('DOKA_E2E_PASSWORD must be provided; no password is committed to the test.');
  17  | });
  18  | 
  19  | async function snapshot(root: string): Promise<Record<string, string>> {
  20  |   const rootInfo = await lstat(root);
  21  |   if (rootInfo.isSymbolicLink() || !rootInfo.isDirectory()) {
  22  |     throw new Error('Acceptance source root must be a real directory, not a symbolic link.');
  23  |   }
  24  |   const output: Record<string, string> = {};
  25  |   async function walk(current: string) {
  26  |     for (const entry of await readdir(current, { withFileTypes: true })) {
  27  |       const full = path.join(current, entry.name);
  28  |       const relative = path.relative(root, full).split(path.sep).join('/');
  29  |       const info = await lstat(full);
  30  |       if (info.isSymbolicLink()) throw new Error(`Acceptance source contains a symbolic link: ${relative}`);
  31  |       if (info.isDirectory()) await walk(full);
  32  |       else if (info.isFile()) output[relative] = createHash('sha256').update(await readFile(full)).digest('hex');
  33  |     }
  34  |   }
  35  |   await walk(root);
  36  |   return output;
  37  | }
  38  | 
  39  | test('Personal Local browser acceptance: login → import → scan → understand → review plan', async ({ page }) => {
  40  |   test.setTimeout(Number(process.env.DOKA_E2E_TEST_TIMEOUT_MS || 120_000));
  41  |   const before = await snapshot(sourceRoot!);
  42  |   const sourceFileCount = Object.keys(before).length;
  43  |   expect(sourceFileCount).toBeGreaterThan(0);
  44  | 
  45  |   await page.goto('/login');
  46  |   await expect(page.getByTestId('login-username')).toBeVisible();
  47  |   await page.getByTestId('login-username').fill(username);
  48  |   await page.getByTestId('login-password').fill(`${password!}-invalid`);
  49  |   await page.getByTestId('login-submit').click();
  50  |   await expect(page.getByRole('alert')).toHaveText('Invalid username or password.');
  51  | 
  52  |   await page.getByTestId('login-password').fill(password!);
  53  |   await page.getByTestId('login-submit').click();
  54  | 
  55  |   await page.waitForURL('**/admin/workspace');
  56  |   await expect(page.getByRole('heading', { name: 'Safe Workspace' })).toBeVisible();
  57  |   await expect(page.getByTestId('start-safe-import')).toBeEnabled();
  58  | 
  59  |   await page.getByTestId('start-safe-import').click();
  60  |   await expect(page.getByText(/Import started\. The original source is not modified\./)).toBeVisible();
> 61  |   await expect(page.getByText('Status:')).toContainText('completed', { timeout: importTimeout });
      |                                           ^ Error: expect(locator).toContainText(expected) failed
  62  |   await expect(page.getByText(/Verified:/)).toContainText(
  63  |     new RegExp(`${sourceFileCount}\\s*/\\s*${sourceFileCount}`),
  64  |   );
  65  |   await expect(page.getByText(/Failed:/)).toHaveText(/Failed:\s*0/);
  66  | 
  67  |   await page.getByTestId('scan-copy').click();
  68  |   await expect(page.getByText('scan completed.')).toBeVisible({ timeout: scanTimeout });
  69  | 
  70  |   const understandingResponsePromise = page.waitForResponse((response) =>
  71  |     response.url().includes('/understanding') && response.request().method() === 'GET',
  72  |   );
  73  |   await page.getByTestId('run-ocr').click();
  74  |   await expect(page.getByText('understand completed.')).toBeVisible({ timeout: understandTimeout });
  75  |   const understandingResponse = await understandingResponsePromise;
  76  |   expect(understandingResponse.ok()).toBeTruthy();
  77  |   const understanding = await understandingResponse.json() as {
  78  |     analyzed_files?: number;
  79  |     results?: Array<{
  80  |       extension?: string;
  81  |       text_length?: number;
  82  |       extraction_method?: string;
  83  |       language?: string;
  84  |     }>;
  85  |   };
  86  |   expect(understanding.analyzed_files).toBe(sourceFileCount);
  87  |   expect(understanding.results).toHaveLength(sourceFileCount);
  88  |   const ocrExtensions = new Set(['.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp']);
  89  |   const ocrResults = understanding.results?.filter((result) =>
  90  |     ocrExtensions.has((result.extension || '').toLowerCase()),
  91  |   ) || [];
  92  |   const successfulOcr = ocrResults.filter((result) =>
  93  |     result.extraction_method !== 'ocr_failed'
  94  |     && result.extraction_method !== 'ocr_failed_dedup'
  95  |     && Boolean(result.text_length),
  96  |   );
  97  |   const languages = new Set(successfulOcr.map((result) => result.language));
  98  |   expect(successfulOcr.some((result) => result.extension?.toLowerCase() === '.pdf')).toBeTruthy();
  99  |   expect(successfulOcr.some((result) => result.extension?.toLowerCase() !== '.pdf')).toBeTruthy();
  100 |   expect([...languages].some((language) => language === 'mya' || language === 'mya+eng')).toBeTruthy();
  101 |   expect([...languages].some((language) => language === 'eng' || language === 'mya+eng')).toBeTruthy();
  102 | 
  103 |   await page.getByTestId('build-review-plan').click();
  104 |   await expect(page.getByText('plan completed.')).toBeVisible({ timeout: planTimeout });
  105 | 
  106 |   await page.reload();
  107 |   await expect(page).toHaveURL(/\/admin\/workspace$/);
  108 |   await expect(page.getByRole('heading', { name: 'Safe Workspace' })).toBeVisible();
  109 | 
  110 |   const after = await snapshot(sourceRoot!);
  111 |   expect(after).toEqual(before);
  112 | });
  113 | 
```