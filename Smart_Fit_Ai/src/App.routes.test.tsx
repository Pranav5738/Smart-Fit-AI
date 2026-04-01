import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import type { ReactNode } from 'react';
import App from '@/App';

vi.mock('@/components/layout/AppLayout', () => ({
  AppLayout: ({ children }: { children: ReactNode }) => <div data-testid="app-layout">{children}</div>,
}));

vi.mock('@/components/layout/AuthShellLayout', () => ({
  AuthShellLayout: ({ children }: { children: ReactNode }) => (
    <div data-testid="auth-shell-layout">{children}</div>
  ),
}));

vi.mock('@/components/ui/PageTransition', () => ({
  PageTransition: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock('@/pages/AuthLandingPage', () => ({
  AuthLandingPage: () => <div>AUTH_LANDING_PAGE</div>,
}));

vi.mock('@/pages/ShowcasePage', () => ({
  ShowcasePage: () => <div>SHOWCASE_PAGE</div>,
}));

vi.mock('@/pages/SignInPage', () => ({
  SignInPage: () => <div>SIGNIN_PAGE</div>,
}));

vi.mock('@/pages/RegisterPage', () => ({
  RegisterPage: () => <div>REGISTER_PAGE</div>,
}));

vi.mock('@/pages/DashboardPage', () => ({
  DashboardPage: () => <div>DASHBOARD_PAGE</div>,
}));

const SESSION_KEY = 'smartfit-auth-session';

const renderAt = (path: string) => {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  );
};

describe('Route Access Matrix', () => {
  it('shows auth landing for unauthenticated home route', async () => {
    renderAt('/');

    expect(await screen.findByText('AUTH_LANDING_PAGE')).toBeTruthy();
  });

  it('redirects unauthenticated dashboard route to sign-in', async () => {
    renderAt('/dashboard');

    expect(await screen.findByText('SIGNIN_PAGE')).toBeTruthy();
  });

  it('redirects unauthenticated upload route to sign-in', async () => {
    renderAt('/upload');

    expect(await screen.findByText('SIGNIN_PAGE')).toBeTruthy();
  });

  it('keeps showcase page publicly accessible', async () => {
    renderAt('/showcase');

    expect(await screen.findByText('SHOWCASE_PAGE')).toBeTruthy();
  });

  it('redirects authenticated home route to dashboard', async () => {
    localStorage.setItem(
      SESSION_KEY,
      JSON.stringify({
        id: 'user-1',
        name: 'Smart Fit User',
        email: 'user@example.com',
      })
    );

    renderAt('/');

    expect(await screen.findByText('DASHBOARD_PAGE')).toBeTruthy();
  });

  it('allows authenticated users to access dashboard directly', async () => {
    localStorage.setItem(
      SESSION_KEY,
      JSON.stringify({
        id: 'user-2',
        name: 'Smart Fit User 2',
        email: 'user2@example.com',
      })
    );

    renderAt('/dashboard');

    expect(await screen.findByText('DASHBOARD_PAGE')).toBeTruthy();
  });

  it('redirects authenticated upload route to dashboard', async () => {
    localStorage.setItem(
      SESSION_KEY,
      JSON.stringify({
        id: 'user-3',
        name: 'Smart Fit User 3',
        email: 'user3@example.com',
      })
    );

    renderAt('/upload');

    expect(await screen.findByText('DASHBOARD_PAGE')).toBeTruthy();
  });
});
