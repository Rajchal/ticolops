import { test, expect } from '@playwright/test';

test.describe('Real-time Collaboration', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/');
    await page.fill('[data-testid="login-email"]', 'test@example.com');
    await page.fill('[data-testid="login-password"]', 'password123');
    await page.click('[data-testid="login-submit"]');
    await expect(page).toHaveURL(/\/dashboard/);
    
    // Navigate to project
    await page.click('[data-testid="project-card"]:first');
  });

  test('should show real-time team presence', async ({ page }) => {
    // Should show current user as online
    await expect(page.locator('[data-testid="team-presence"]')).toContainText('Test User');
    await expect(page.locator('[data-testid="user-status"]:has-text("Test User")')).toHaveClass(/online/);
    
    // Should show user activity location
    await expect(page.locator('[data-testid="user-location"]')).toContainText('Dashboard');
  });

  test('should update user status in real-time', async ({ page }) => {
    // Simulate user going idle
    await page.evaluate(() => {
      // Simulate 5 minutes of inactivity
      window.dispatchEvent(new Event('user-idle'));
    });
    
    // Wait for status update
    await page.waitForTimeout(1000);
    
    // Should show away status
    await expect(page.locator('[data-testid="user-status"]:has-text("Test User")')).toHaveClass(/away/);
    
    // Simulate user activity
    await page.mouse.move(100, 100);
    await page.waitForTimeout(1000);
    
    // Should show online status
    await expect(page.locator('[data-testid="user-status"]:has-text("Test User")')).toHaveClass(/online/);
  });

  test('should show activity feed in real-time', async ({ page }) => {
    // Navigate to different section
    await page.click('[data-testid="repository-tab"]');
    
    // Should show activity in feed
    await expect(page.locator('[data-testid="activity-feed"]')).toContainText('Test User is viewing Repository');
    
    // Navigate to another section
    await page.click('[data-testid="deployments-tab"]');
    
    // Should show new activity
    await expect(page.locator('[data-testid="activity-feed"]')).toContainText('Test User is viewing Deployments');
  });

  test('should detect and show conflicts', async ({ page }) => {
    // Simulate conflict scenario
    await page.evaluate(() => {
      // Mock WebSocket message for conflict detection
      window.dispatchEvent(new CustomEvent('websocket-message', {
        detail: {
          type: 'conflict_detected',
          payload: {
            location: 'src/components/Header.tsx',
            users: ['Test User', 'Teammate'],
            severity: 'medium'
          }
        }
      }));
    });
    
    // Should show conflict notification
    await expect(page.locator('[data-testid="conflict-notification"]')).toBeVisible();
    await expect(page.locator('[data-testid="conflict-location"]')).toContainText('src/components/Header.tsx');
    await expect(page.locator('[data-testid="conflict-users"]')).toContainText('Test User, Teammate');
  });

  test('should show collaboration opportunities', async ({ page }) => {
    // Simulate collaboration opportunity
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('websocket-message', {
        detail: {
          type: 'collaboration_opportunity',
          payload: {
            location: 'src/services/api.ts',
            users: ['Test User', 'Teammate'],
            type: 'related_work'
          }
        }
      }));
    });
    
    // Should show collaboration suggestion
    await expect(page.locator('[data-testid="collaboration-suggestion"]')).toBeVisible();
    await expect(page.locator('[data-testid="suggestion-text"]')).toContainText('You and Teammate are working on related components');
  });

  test('should handle WebSocket connection loss and reconnection', async ({ page }) => {
    // Simulate WebSocket disconnection
    await page.evaluate(() => {
      window.dispatchEvent(new Event('websocket-disconnect'));
    });
    
    // Should show connection status
    await expect(page.locator('[data-testid="connection-status"]')).toContainText('Disconnected');
    await expect(page.locator('[data-testid="reconnect-indicator"]')).toBeVisible();
    
    // Simulate reconnection
    await page.evaluate(() => {
      window.dispatchEvent(new Event('websocket-reconnect'));
    });
    
    // Should show connected status
    await expect(page.locator('[data-testid="connection-status"]')).toContainText('Connected');
    await expect(page.locator('[data-testid="reconnect-indicator"]')).not.toBeVisible();
  });

  test('should send and receive real-time notifications', async ({ page }) => {
    // Simulate receiving notification
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('websocket-message', {
        detail: {
          type: 'notification',
          payload: {
            id: '123',
            title: 'Deployment Successful',
            message: 'Your latest deployment to staging is now live',
            type: 'success',
            timestamp: new Date().toISOString()
          }
        }
      }));
    });
    
    // Should show notification
    await expect(page.locator('[data-testid="notification-toast"]')).toBeVisible();
    await expect(page.locator('[data-testid="notification-title"]')).toContainText('Deployment Successful');
    await expect(page.locator('[data-testid="notification-message"]')).toContainText('Your latest deployment to staging is now live');
  });
});