import { mkdir, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';
import { test, expect } from './fixtures';

test('the token import does not expose private project files through Vite', async ({ request }, info) => {
  // A synthetic marker in the private report directory, never a real private file.
  const probe = info.outputPath('synthetic-private.txt');
  await mkdir(dirname(probe), { recursive: true });
  await writeFile(probe, 'Synthetic private boundary probe.');
  const response = await request.get(`/@fs${probe}`);
  expect(response.status()).toBe(403);
});
