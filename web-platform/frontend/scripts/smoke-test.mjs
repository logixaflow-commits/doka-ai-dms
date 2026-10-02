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
]) {
  if (!cloudApi.includes(required)) throw new Error(`Cloud Worker is missing ${required}.`);
}
if (!cloudPage.includes('Version history') || !cloudPage.includes('Restore this version') || !cloudPage.includes('Save new version')) {
  throw new Error('Cloud document version history UI is missing.');
}
const auditPage = fs.readFileSync(path.resolve('src/pages/CloudAudit.tsx'), 'utf8');
if (!app.includes('path="activity"') || !auditPage.includes('listCloudAuditEvents')) {
  throw new Error('Owner-scoped Activity page is not wired into the application.');
}
console.log('Cloud versioning, preview and audit smoke tests passed.');

const contract = JSON.parse(fs.readFileSync(path.resolve('../../shared/contracts/cloud-document.schema.json'), 'utf8'));
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
