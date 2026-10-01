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
  '/rest/v1/doka_documents',
  '/storage/v1/object/',
  '/storage/v1/object/sign/',
  'crypto.subtle.digest',
  'getCurrentUser',
  'x-upsert',
]) {
  if (!cloudDocuments.includes(required)) {
    throw new Error(`Cloud document Supabase integration is missing: ${required}`);
  }
}
if (cloudDocuments.includes("|| '/api'")) {
  throw new Error('Cloud documents must not silently route to the frontend SPA /api fallback.');
}
console.log('Supabase cloud document integration smoke test passed.');

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
