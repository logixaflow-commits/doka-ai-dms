import { describe, expect, it } from 'vitest';
import { getAuthStorageMode } from './supabaseAuth';

describe('auth storage mode', () => {
  it('keeps the existing localStorage session mode until the BFF migration is implemented', () => {
    expect(getAuthStorageMode()).toBe('local');
  });
});
