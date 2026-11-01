import { screen } from '@testing-library/react';
import { act } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('development entry point', () => {
  beforeEach(() => {
    vi.resetModules();
    document.body.replaceChildren();
    vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 401 })));
  });
  afterEach(() => vi.unstubAllGlobals());

  it('mounts the scaffold in the HTML root', async () => {
    const container = document.createElement('div');
    container.id = 'root';
    document.body.append(container);
    let mountedRoot: import('react-dom/client').Root | null = null;
    try {
      await act(async () => {
        mountedRoot = (await import('./main')).mountedRoot;
      });
      expect(screen.getByRole('heading', { name: /Your budget/ })).toBeTruthy();
    } finally {
      await act(async () => { mountedRoot?.unmount(); });
      container.remove();
    }
  });

  it('does not mount without a root container', async () => {
    const { mountedRoot } = await import('./main');
    expect(mountedRoot).toBeNull();
    expect(screen.queryByRole('heading')).toBeNull();
  });
});
