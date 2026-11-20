import { describe, expect, it } from 'vitest';

// Deliberately failing test for the CI pipeline check. Reverted in the next commit.
describe('pipeline check', () => {
  it('fails on purpose', () => {
    expect(1 + 1).toBe(3);
  });
});
