# Testing Guide

This document provides comprehensive information about testing in the Ticolops platform.

## Table of Contents

1. [Testing Strategy](#testing-strategy)
2. [Test Types](#test-types)
3. [Frontend Testing](#frontend-testing)
4. [Backend Testing](#backend-testing)
5. [End-to-End Testing](#end-to-end-testing)
6. [CI/CD Integration](#cicd-integration)
7. [Best Practices](#best-practices)

## Testing Strategy

Our testing strategy follows the testing pyramid approach:

```
    /\
   /  \     E2E Tests (Few)
  /____\    
 /      \   Integration Tests (Some)
/__________\ Unit Tests (Many)
```

### Test Coverage Goals

- **Unit Tests**: 80%+ coverage
- **Integration Tests**: Critical user flows
- **E2E Tests**: Key user journeys

## Test Types

### 1. Unit Tests
- Test individual components and functions in isolation
- Fast execution and immediate feedback
- Mock external dependencies

### 2. Integration Tests
- Test interaction between multiple components
- Verify API endpoints and database operations
- Test real data flows

### 3. End-to-End Tests
- Test complete user workflows
- Verify the entire application stack
- Simulate real user interactions

## Frontend Testing

### Setup

The frontend uses Vitest for unit testing and Playwright for E2E testing.

```bash
cd frontend
npm install
npm run test        # Run unit tests
npm run e2e         # Run E2E tests
```

### Unit Testing with Vitest

#### Configuration

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      thresholds: {
        global: {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80
        }
      }
    }
  }
});
```

#### Writing Unit Tests

```typescript
// components/__tests__/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '../Button';

describe('Button', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('applies correct CSS classes', () => {
    render(<Button variant="primary">Primary Button</Button>);
    const button = screen.getByText('Primary Button');
    expect(button).toHaveClass('bg-blue-500');
  });
});
```

#### Testing Custom Hooks

```typescript
// hooks/__tests__/useProjects.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useProjects } from '../useProjects';
import { server } from '../../test/mocks/server';

describe('useProjects', () => {
  it('fetches projects on mount', async () => {
    const { result } = renderHook(() => useProjects());

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.projects).toHaveLength(2);
    expect(result.current.error).toBeNull();
  });

  it('handles fetch error', async () => {
    server.use(
      rest.get('/api/projects', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ error: 'Server error' }));
      })
    );

    const { result } = renderHook(() => useProjects());

    await waitFor(() => {
      expect(result.current.error).toBe('Server error');
    });
  });
});
```

#### Testing Context Providers

```typescript
// contexts/__tests__/AuthContext.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../AuthContext';

const TestComponent = () => {
  const { state, login, logout } = useAuth();
  
  return (
    <div>
      <div data-testid="auth-status">
        {state.isAuthenticated ? 'Authenticated' : 'Not authenticated'}
      </div>
      <button onClick={() => login('test@example.com', 'password')}>
        Login
      </button>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

describe('AuthContext', () => {
  it('provides authentication state', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth-status')).toHaveTextContent('Not authenticated');
  });

  it('handles login', async () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    fireEvent.click(screen.getByText('Login'));

    await waitFor(() => {
      expect(screen.getByTestId('auth-status')).toHaveTextContent('Authenticated');
    });
  });
});
```

### Mock Service Worker (MSW)

We use MSW to mock API calls in tests:

```typescript
// test/mocks/handlers.ts
import { rest } from 'msw';

export const handlers = [
  rest.get('/api/projects', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          items: [
            { id: '1', name: 'Test Project', description: 'A test project' }
          ]
        }
      })
    );
  }),
];
```

### E2E Testing with Playwright

#### Configuration

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html'], ['json'], ['junit']],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'Mobile Chrome', use: { ...devices['Pixel 5'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
});
```

#### Writing E2E Tests

```typescript
// e2e/auth.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('should login successfully', async ({ page }) => {
    await page.goto('/');
    
    await page.fill('[placeholder="Enter your email"]', 'test@example.com');
    await page.fill('[placeholder="Enter your password"]', 'password123');
    await page.click('button:has-text("Sign In")');
    
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('h1')).toContainText('Dashboard');
  });

  test('should show validation errors', async ({ page }) => {
    await page.goto('/');
    
    await page.click('button:has-text("Sign In")');
    
    await expect(page.locator('text=Email is required')).toBeVisible();
    await expect(page.locator('text=Password is required')).toBeVisible();
  });
});
```

#### Page Object Model

```typescript
// e2e/pages/LoginPage.ts
import { Page, Locator } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.locator('[placeholder="Enter your email"]');
    this.passwordInput = page.locator('[placeholder="Enter your password"]');
    this.loginButton = page.locator('button:has-text("Sign In")');
    this.errorMessage = page.locator('[data-testid="error-message"]');
  }

  async goto() {
    await this.page.goto('/');
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.loginButton.click();
  }

  async expectErrorMessage(message: string) {
    await expect(this.errorMessage).toContainText(message);
  }
}
```

## Backend Testing

### Setup

The backend uses Jest for unit and integration testing.

```bash
cd backend
npm install
npm run test              # Run all tests
npm run test:unit         # Run unit tests only
npm run test:integration  # Run integration tests only
```

### Unit Testing

```typescript
// services/__tests__/ProjectService.test.ts
import { ProjectService } from '../ProjectService';
import { prismaMock } from '../../test/mocks/prisma';

describe('ProjectService', () => {
  let projectService: ProjectService;

  beforeEach(() => {
    projectService = new ProjectService();
  });

  describe('getProjectsForUser', () => {
    it('returns projects for authenticated user', async () => {
      const mockProjects = [
        { id: '1', name: 'Test Project', ownerId: 'user-1' }
      ];

      prismaMock.project.findMany.mockResolvedValue(mockProjects);
      prismaMock.project.count.mockResolvedValue(1);

      const result = await projectService.getProjectsForUser('user-1', {});

      expect(result.items).toEqual(mockProjects);
      expect(result.pagination.total).toBe(1);
    });

    it('filters projects by search term', async () => {
      const mockProjects = [
        { id: '1', name: 'React Project', ownerId: 'user-1' }
      ];

      prismaMock.project.findMany.mockResolvedValue(mockProjects);
      prismaMock.project.count.mockResolvedValue(1);

      await projectService.getProjectsForUser('user-1', { search: 'React' });

      expect(prismaMock.project.findMany).toHaveBeenCalledWith(
        expect.objectContaining({
          where: expect.objectContaining({
            OR: expect.arrayContaining([
              { name: { contains: 'React', mode: 'insensitive' } }
            ])
          })
        })
      );
    });
  });
});
```

### Integration Testing

```typescript
// tests/integration/projects.test.ts
import request from 'supertest';
import { app } from '../../src/app';
import { createTestUser, createAuthToken } from '../helpers/auth';
import { cleanupDatabase } from '../helpers/database';

describe('Projects API', () => {
  let authToken: string;
  let userId: string;

  beforeEach(async () => {
    await cleanupDatabase();
    const user = await createTestUser();
    userId = user.id;
    authToken = createAuthToken(user);
  });

  describe('GET /api/projects', () => {
    it('returns projects for authenticated user', async () => {
      // Create test project
      await request(app)
        .post('/api/projects')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          name: 'Test Project',
          description: 'A test project'
        });

      const response = await request(app)
        .get('/api/projects')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.items).toHaveLength(1);
      expect(response.body.data.items[0].name).toBe('Test Project');
    });

    it('supports pagination', async () => {
      // Create multiple projects
      for (let i = 1; i <= 25; i++) {
        await request(app)
          .post('/api/projects')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            name: `Project ${i}`,
            description: `Description ${i}`
          });
      }

      const response = await request(app)
        .get('/api/projects?page=2&limit=10')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.data.items).toHaveLength(10);
      expect(response.body.data.pagination.page).toBe(2);
      expect(response.body.data.pagination.total).toBe(25);
    });
  });
});
```

### Database Testing Helpers

```typescript
// tests/helpers/database.ts
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

export async function cleanupDatabase() {
  await prisma.deployment.deleteMany();
  await prisma.repository.deleteMany();
  await prisma.projectMember.deleteMany();
  await prisma.project.deleteMany();
  await prisma.user.deleteMany();
}

export async function createTestUser(overrides = {}) {
  return prisma.user.create({
    data: {
      name: 'Test User',
      email: 'test@example.com',
      password: 'hashedpassword',
      role: 'student',
      ...overrides
    }
  });
}
```

## CI/CD Integration

### GitHub Actions Workflow

Our CI/CD pipeline runs tests automatically:

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 18
      - run: cd frontend && npm ci
      - run: cd frontend && npm run test:coverage
      - run: cd frontend && npm run build

  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 18
      - run: cd backend && npm ci
      - run: cd backend && npm run test:coverage

  e2e-tests:
    runs-on: ubuntu-latest
    needs: [frontend-tests, backend-tests]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 18
      - run: cd frontend && npm ci && npx playwright install
      - run: cd backend && npm ci
      - run: cd frontend && npm run e2e
```

### Test Reports

- **Coverage Reports**: Generated by Vitest and Jest
- **E2E Reports**: Generated by Playwright
- **Test Results**: Uploaded to GitHub Actions artifacts

## Best Practices

### General Testing Principles

1. **Write tests first** (TDD approach when possible)
2. **Test behavior, not implementation**
3. **Keep tests simple and focused**
4. **Use descriptive test names**
5. **Arrange, Act, Assert pattern**

### Frontend Testing Best Practices

1. **Test user interactions, not implementation details**
2. **Use semantic queries** (`getByRole`, `getByLabelText`)
3. **Mock external dependencies**
4. **Test accessibility** (screen readers, keyboard navigation)
5. **Test responsive behavior**

### Backend Testing Best Practices

1. **Test business logic thoroughly**
2. **Use real database for integration tests**
3. **Test error conditions**
4. **Validate input/output schemas**
5. **Test authentication and authorization**

### E2E Testing Best Practices

1. **Focus on critical user journeys**
2. **Use Page Object Model for maintainability**
3. **Keep tests independent**
4. **Use data attributes for stable selectors**
5. **Test across different browsers and devices**

### Test Data Management

1. **Use factories for test data creation**
2. **Clean up after each test**
3. **Use realistic but anonymized data**
4. **Avoid hardcoded values**

### Performance Considerations

1. **Run unit tests in parallel**
2. **Use test databases for isolation**
3. **Mock slow external services**
4. **Optimize CI/CD pipeline**

## Debugging Tests

### Frontend Test Debugging

```bash
# Run tests in watch mode
npm run test:watch

# Run tests with UI
npm run test:ui

# Debug specific test
npm run test -- --reporter=verbose ComponentName
```

### E2E Test Debugging

```bash
# Run tests in headed mode
npm run e2e:headed

# Debug tests step by step
npm run e2e:debug

# Run tests with UI
npm run e2e:ui
```

### Backend Test Debugging

```bash
# Run tests in watch mode
npm run test:watch

# Debug specific test file
npm run test -- --testPathPattern=ProjectService

# Run tests with verbose output
npm run test -- --verbose
```

## Continuous Improvement

### Monitoring Test Health

1. **Track test execution time**
2. **Monitor test flakiness**
3. **Review coverage reports regularly**
4. **Update tests when features change**

### Test Maintenance

1. **Remove obsolete tests**
2. **Refactor duplicated test code**
3. **Update test dependencies**
4. **Review and improve test documentation**

---

For more information about specific testing scenarios or troubleshooting, check our [GitHub Discussions](https://github.com/ticolops/platform/discussions) or contact the development team.