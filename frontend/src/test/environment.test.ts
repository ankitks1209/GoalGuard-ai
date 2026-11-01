import { expect, it } from 'vitest';

it('enables React act support for entry-point tests with explicit Vitest hooks', () => {
  expect(globalThis).toHaveProperty('IS_REACT_ACT_ENVIRONMENT', true);
});
