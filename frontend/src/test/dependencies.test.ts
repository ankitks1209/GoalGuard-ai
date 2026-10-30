import { readFileSync } from 'node:fs';
import { expect, it } from 'vitest';

// Dependency-state regression for GHSA-82fw-gwwq-j7x9, not an exploit test.
// 4.1.12 includes the follow-up mock hardening as well as the initial patch.
function hardenedStable(version: string): boolean {
  const parts = /^(\d+)\.(\d+)\.(\d+)$/.exec(version);
  if (!parts) return false;
  const major = Number(parts[1]);
  const minor = Number(parts[2]);
  const patch = Number(parts[3]);
  return major > 4 || (major === 4 && (minor > 1 || (minor === 1 && patch >= 12)));
}

function read(relative: string) {
  return JSON.parse(readFileSync(new URL(relative, import.meta.url), 'utf8'));
}

it('pins matching hardened Vitest and coverage versions in manifest and lock', () => {
  const manifest = read('../../package.json');
  const lock = read('../../package-lock.json');
  const version = manifest.devDependencies.vitest;
  expect(hardenedStable(version)).toBe(true);
  expect(manifest.devDependencies['@vitest/coverage-v8']).toBe(version);
  expect(lock.packages[''].devDependencies.vitest).toBe(version);
  expect(lock.packages[''].devDependencies['@vitest/coverage-v8']).toBe(version);
  expect(lock.packages['node_modules/vitest'].version).toBe(version);
  expect(lock.packages['node_modules/@vitest/coverage-v8'].version).toBe(version);
  const mockers = Object.entries(lock.packages).filter(([path]) =>
    path.endsWith('node_modules/@vitest/mocker'));
  expect(mockers.length).toBeGreaterThan(0);
  for (const [, dependency] of mockers) {
    expect(hardenedStable((dependency as { version: string }).version)).toBe(true);
  }
});

it('uses hardened installed test tooling, not only a changed manifest', () => {
  const manifest = read('../../package.json');
  for (const name of ['vitest', '@vitest/coverage-v8', '@vitest/mocker']) {
    const installed = read(`../../node_modules/${name}/package.json`);
    expect(hardenedStable(installed.version)).toBe(true);
    expect(installed.version).toBe(manifest.devDependencies.vitest);
  }
});
