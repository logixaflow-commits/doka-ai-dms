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
