import fs from 'node:fs';
import path from 'node:path';

const required = [
  'src/App.tsx',
  'src/pages/WorkspaceReview.tsx',
  'src/components/ui/button.tsx',
  'src/lib/utils.ts',
];

for (const file of required) {
  const full = path.resolve(file);
  if (!fs.existsSync(full)) throw new Error(`Missing frontend file: ${file}`);
}

const workspace = fs.readFileSync(path.resolve('src/pages/WorkspaceReview.tsx'), 'utf8');
if (!workspace.includes('/imports')) throw new Error('Workspace session API wiring is missing.');
if (!workspace.includes('approve')) throw new Error('Workspace approval UI wiring is missing.');

const runStep = workspace.slice(
  workspace.indexOf('async function runStep'),
  workspace.indexOf('async function validateOcr')
);
const runRequestIndex = runStep.indexOf('const response = await api');
for (const reset of ['setProposals([])', 'setSelected(new Set())']) {
  if (runStep.indexOf(reset) < 0 || runStep.indexOf(reset) > runRequestIndex) {
    throw new Error(`Workspace ${reset} must run before the scan/OCR/plan request.`);
  }
}
for (const reset of ['setSearchResults([])', 'setOcrResults([])', 'setEditingOcr(null)', 'setOcrDraft(\'\')']) {
  if (!runStep.includes(reset)) throw new Error(`Workspace step reset is missing ${reset}.`);
}
const startImport = workspace.slice(
  workspace.indexOf('async function startImport'),
  workspace.indexOf('const loadStatus')
);
if (!startImport.includes('setSearchResults([])')) {
  throw new Error('Starting a new import must clear previous session search results.');
}

const themeContext = fs.readFileSync(path.resolve('src/contexts/ThemeContext.tsx'), 'utf8');
for (const required of [
  'typeof window === \'undefined\'',
  'window.localStorage.getItem',
  'window.localStorage.setItem',
  'useCallback',
  'useMemo',
  "media.addEventListener('change', applyTheme)",
  "media.removeEventListener('change', applyTheme)",
]) {
  if (!themeContext.includes(required)) {
    throw new Error(`ThemeContext safety or memoization contract is missing ${required}.`);
  }
}
console.log('ThemeContext storage, system-theme and memoization smoke test passed.');

console.log('Frontend smoke test passed.');

const cloudDocuments = fs.readFileSync(path.resolve('src/lib/cloudDocuments.ts'), 'utf8');
for (const required of [
  'VITE_API_BASE_URL',
  'getAccessToken',
  'getCurrentUser',
  'refreshSession',
  'Authorization:',
  'FormData',
  '/documents?',
  '/download',
  'method: \'PATCH\'',
]) {
  if (!cloudDocuments.includes(required)) {
    throw new Error(`FastAPI cloud document integration is missing: ${required}`);
  }
}
for (const forbidden of ['/rest/v1/doka_documents', '/storage/v1/object/', 'x-upsert']) {
  if (cloudDocuments.includes(forbidden)) {
    throw new Error(`Frontend must not call Supabase data/storage endpoints directly: ${forbidden}`);
  }
}
console.log('FastAPI cloud document integration smoke test passed.');

const sidebar = fs.readFileSync(path.resolve('src/components/ui/sidebar.tsx'), 'utf8');
if (!sidebar.includes('hidden shrink-0 md:block')) {
  throw new Error('Desktop sidebar must reserve its layout width instead of shrinking over page content.');
}
console.log('Desktop sidebar layout regression test passed.');

const app = fs.readFileSync(path.resolve('src/App.tsx'), 'utf8');
const layout = fs.readFileSync(path.resolve('src/layouts/AdminLayout.tsx'), 'utf8');
const cloudPage = fs.readFileSync(path.resolve('src/pages/CloudDocuments.tsx'), 'utf8');
if (!app.includes('path="cloud-documents"') || !layout.includes('/admin/cloud-documents')) {
  throw new Error('Cloud Documents page is not reachable from the authenticated app navigation.');
}
for (const required of ['uploadCloudDocument', 'listCloudDocuments', 'getCloudDocumentDownloadUrl', 'updateCloudDocument']) {
  if (!cloudPage.includes(required)) throw new Error(`Cloud Documents UI is missing ${required}.`);
}
console.log('Cloud Documents UI route smoke test passed.');

const cloudApi = fs.readFileSync(path.resolve('../../cloudflare_worker/main.py'), 'utf8');
for (const required of [
  'search: str | None',
  'deleted_at=is.null',
  'async def trash_document',
  'async def restore_document',
  'def _normalize_folder_path',
  'filename: str | None',
]) {
  if (!cloudApi.includes(required)) throw new Error(`Cloud API lifecycle feature is missing: ${required}`);
}
for (const required of ['trashCloudDocument', 'restoreCloudDocument', 'renameCloudDocument', 'moveCloudDocument']) {
  if (!cloudDocuments.includes(required)) throw new Error(`Cloud frontend client is missing ${required}.`);
}
if (!cloudPage.includes('Trash') || !cloudPage.includes('Search file names') || !cloudPage.includes('Load more documents')) {
  throw new Error('Cloud document search, pagination or trash UI is missing.');
}
console.log('Cloud library lifecycle smoke test passed.');

for (const required of [
  'getCloudDocumentPreviewUrl',
  'listCloudDocumentVersions',
  'createCloudDocumentVersion',
  'restoreCloudDocumentVersion',
  'bulkUpdateCloudDocuments',
  'listCloudFolders',
  'permanentlyDeleteCloudDocument',
]) {
  if (!cloudDocuments.includes(required)) throw new Error(`Cloud client is missing ${required}.`);
}
for (const required of [
  '/api/documents/{document_id}/preview',
  '/api/documents/{document_id}/versions',
  'doka_replace_document_version',
  'doka_restore_document_version',
  'version_create',
  'version_restore',
  'doka_bulk_update_documents',
  '/api/folders',
]) {
  if (!cloudApi.includes(required)) throw new Error(`Cloud Worker is missing ${required}.`);
}
if (!cloudPage.includes('Version history') || !cloudPage.includes('Restore this version') || !cloudPage.includes('Save new version')) {
  throw new Error('Cloud document version history UI is missing.');
}
if (!cloudPage.includes('Batch upload queue') || !cloudPage.includes('Retry failed') || !cloudPage.includes('processBatch')) {
  throw new Error('Cloud batch upload queue and retry controls are missing.');
}
const auditPage = fs.readFileSync(path.resolve('src/pages/CloudAudit.tsx'), 'utf8');
if (!app.includes('path="activity"') || !auditPage.includes('listCloudAuditEvents')) {
  throw new Error('Owner-scoped Activity page is not wired into the application.');
}
console.log('Cloud versioning, preview and audit smoke tests passed.');

const contract = JSON.parse(fs.readFileSync(path.resolve('../../cloudflare_worker/shared/contracts/cloud-document.schema.json'), 'utf8'));
for (const field of ['id', 'owner_id', 'object_key', 'filename', 'sha256', 'deleted_at', 'folder_path']) {
  if (!contract.required.includes(field)) throw new Error(`Canonical document contract is missing ${field}.`);
}
for (const status of ['active', 'review', 'quarantined', 'archived']) {
  if (!contract.properties.status.enum.includes(status)) throw new Error(`Canonical document contract is missing status ${status}.`);
}
if (!cloudApi.includes('allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"]')) {
  throw new Error('Cloud API CORS does not allow the authenticated Trash operation.');
}
console.log('Doka Cloud API schema and security contract smoke test passed.');

const folderPattern = new RegExp(contract.properties.folder_path.pattern);
for (const [value, expected] of [['/', true], ['/Finance/Invoices', true], ['/some..name', true], ['/../etc', false], ['/a/../b', false], ['/a/', false], ['//a', false], ['/a\\\\b', false]]) {
  if (folderPattern.test(value) !== expected) throw new Error(`Folder path schema mismatch for ${value}.`);
}
console.log('Doka folder path schema validation passed.');


const localAuth = fs.readFileSync(path.resolve('src/lib/localAuth.ts'), 'utf8');
const adminLayout = fs.readFileSync(path.resolve('src/layouts/AdminLayout.tsx'), 'utf8');
if (!localAuth.includes("VITE_DOKA_EDITION === 'personal-local'")) {
  throw new Error('Packaged Personal Local Edition must have an explicit production build flag.');
}
if (!localAuth.includes("if (import.meta.env.VITE_DOKA_EDITION === 'personal-local') return true;")) {
  throw new Error('Explicit Personal Local builds must not switch to Supabase when its credentials are present.');
}
if (!adminLayout.includes("isLocalAuthEnabled()")) {
  throw new Error('Admin navigation must use the shared local-edition detection rule.');
}
console.log('Personal Local production build boundary smoke test passed.');

if (!localAuth.includes('export async function signOutLocal()') || !localAuth.includes('/auth/logout')) {
  throw new Error('Personal Local logout must call the backend before clearing browser credentials.');
}
if (!adminLayout.includes('signOutLocal()')) {
  throw new Error('Personal Local navigation must use the local session logout flow.');
}
console.log('Personal Local logout boundary smoke test passed.');

const cloudAuth = fs.readFileSync(path.resolve('src/lib/supabaseAuth.ts'), 'utf8');
if (!localAuth.includes("doka_local_access_token") || !localAuth.includes("doka_local_refresh_token") || !localAuth.includes("doka_local_user")) {
  throw new Error('Personal Local auth state must use an edition-specific storage namespace.');
}
if (!cloudAuth.includes("doka_cloud_access_token") || !cloudAuth.includes("doka_cloud_refresh_token") || !cloudAuth.includes("doka_cloud_user")) {
  throw new Error('Personal Cloud auth state must use an edition-specific storage namespace.');
}
if (localAuth.includes("const ACCESS_TOKEN_KEY = 'access_token'") || cloudAuth.includes("const ACCESS_TOKEN_KEY = 'access_token'")) {
  throw new Error('Local and Cloud auth must not share generic browser token keys.');
}
console.log('Local/Cloud browser session storage isolation smoke test passed.');



const serviceWorker = fs.readFileSync(path.resolve('public/sw.js'), 'utf8');
for (const required of [
  "request.method !== 'GET'",
  "request.headers.has('Authorization')",
  "url.origin !== self.location.origin || url.search",
  "url.pathname === '/api'",
  "url.pathname.startsWith('/api/')",
  "url.pathname.startsWith('/auth/')",
  "url.pathname.startsWith('/assets/')",
]) {
  if (!serviceWorker.includes(required)) {
    throw new Error(`Service Worker cache boundary is missing ${required}.`);
  }
}
if (serviceWorker.includes('caches.match(event.request)')) {
  throw new Error('Service Worker must not cache arbitrary API or document requests.');
}
console.log('Service Worker private-content cache boundary smoke test passed.');
