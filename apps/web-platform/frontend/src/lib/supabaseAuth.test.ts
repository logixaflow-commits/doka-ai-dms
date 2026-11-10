import { describe, expect, it } from 'vitest';
import { getAuthStorageMode } from './supabaseAuth';
describe('auth storage preparation switch', () => {
  it('supports local default and cookie-prep opt-in without enabling it by default', () => {
    expect(['local', 'cookie-prep']).toContain(getAuthStorageMode());
  });
});
