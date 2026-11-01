import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

declare global {
  var IS_REACT_ACT_ENVIRONMENT: boolean;
}

// Vitest hooks are imported explicitly, so Testing Library's global-hook setup
// does not enable this flag for entry-point tests that call React.act directly.
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

afterEach(() => cleanup());
