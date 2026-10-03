import { renderHook, act } from '@testing-library/react';
import { AuthProvider, useAuthSession } from './useAuthSession';

test('login e logout funcionam no hook', () => {
  const wrapper = ({ children }: { children: React.ReactNode }) => <AuthProvider>{children}</AuthProvider>;
  const { result } = renderHook(() => useAuthSession(), { wrapper });

  act(() => {
    result.current.login('token-123', { id: '1', name: 'Dev', role: 'admin' });
  });

  expect(result.current.isAuthenticated).toBe(true);
  expect(result.current.user?.name).toBe('Dev');

  act(() => {
    result.current.logout();
  });

  expect(result.current.isAuthenticated).toBe(false);
});
