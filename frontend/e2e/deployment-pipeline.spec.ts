import { test, expect } from '@playwright/test';

test.describe('Deployment Pipeline', () => {
  test.beforeEach(async ({ page }) => {
    // Login and navigate to project
    await page.goto('/');
    await page.fill('[data-testid="login-email"]', 'test@example.com');
    await page.fill('[data-testid="login-password"]', 'password123');
    await page.click('[data-testid="login-submit"]');
    await expect(page).toHaveURL(/\/dashboard/);
    await page.click('[data-testid="project-card"]:first');
    await page.click('[data-testid="deployments-tab"]');
  });

  test('should trigger manual deployment', async ({ page }) => {
    // Trigger deployment
    await page.click('[data-testid="deploy-button"]');
    await page.selectOption('[data-testid="deployment-branch"]', 'main');
    await page.selectOption('[data-testid="deployment-environment"]', 'staging');
    await page.click('[data-testid="confirm-deploy"]');
    
    // Should show deployment in progress
    await expect(page.locator('[data-testid="deployment-status"]')).toContainText('Building');
    await expect(page.locator('[data-testid="deployment-progress"]')).toBeVisible();
  });

  test('should show deployment history', async ({ page }) => {
    // Should display deployment list
    await expect(page.locator('[data-testid="deployment-list"]')).toBeVisible();
    
    // Should show deployment details
    const firstDeployment = page.locator('[data-testid="deployment-item"]:first');
    await expect(firstDeployment.locator('[data-testid="deployment-branch"]')).toBeVisible();
    await expect(firstDeployment.locator('[data-testid="deployment-commit"]')).toBeVisible();
    await expect(firstDeployment.locator('[data-testid="deployment-timestamp"]')).toBeVisible();
  });

  test('should handle successful deployment', async ({ page }) => {
    // Simulate successful deployment
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('websocket-message', {
        detail: {
          type: 'deployment_status',
          payload: {
            id: 'deploy-123',
            status: 'success',
            url: 'https://staging.example.com',
            branch: 'main',
            commit: 'abc123',
            logs: ['Building...', 'Tests passed', 'Deployment successful']
          }
        }
      }));
    });
    
    // Should show success status
    await expect(page.locator('[data-testid="deployment-status"]')).toContainText('Success');
    await expect(page.locator('[data-testid="deployment-url"]')).toContainText('https://staging.example.com');
    
    // Should show preview link
    await expect(page.locator('[data-testid="preview-link"]')).toBeVisible();
    await expect(page.locator('[data-testid="preview-link"]')).toHaveAttribute('href', 'https://staging.example.com');
  });

  test('should handle failed deployment', async ({ page }) => {
    // Simulate failed deployment
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('websocket-message', {
        detail: {
          type: 'deployment_status',
          payload: {
            id: 'deploy-456',
            status: 'failed',
            branch: 'feature-branch',
            commit: 'def456',
            error: 'Build failed: Missing dependency',
            logs: ['Building...', 'npm install failed', 'Error: Module not found']
          }
        }
      }));
    });
    
    // Should show failure status
    await expect(page.locator('[data-testid="deployment-status"]')).toContainText('Failed');
    await expect(page.locator('[data-testid="deployment-error"]')).toContainText('Build failed: Missing dependency');
    
    // Should show retry button
    await expect(page.locator('[data-testid="retry-deployment"]')).toBeVisible();
  });

  test('should show deployment logs', async ({ page }) => {
    // Click on deployment to view details
    await page.click('[data-testid="deployment-item"]:first');
    
    // Should show logs panel
    await expect(page.locator('[data-testid="deployment-logs"]')).toBeVisible();
    
    // Should show log entries
    await expect(page.locator('[data-testid="log-entry"]')).toHaveCount.greaterThan(0);
    
    // Should be able to filter logs
    await page.selectOption('[data-testid="log-level-filter"]', 'error');
    await expect(page.locator('[data-testid="log-entry"]:visible')).toHaveCount.lessThanOrEqual(3);
  });

  test('should handle webhook-triggered deployment', async ({ page }) => {
    // Simulate webhook deployment
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('websocket-message', {
        detail: {
          type: 'deployment_triggered',
          payload: {
            id: 'deploy-789',
            trigger: 'webhook',
            branch: 'main',
            commit: 'ghi789',
            author: 'developer@example.com',
            message: 'Fix: Update API endpoint'
          }
        }
      }));
    });
    
    // Should show new deployment
    await expect(page.locator('[data-testid="deployment-list"]')).toContainText('deploy-789');
    await expect(page.locator('[data-testid="deployment-trigger"]')).toContainText('Webhook');
    await expect(page.locator('[data-testid="deployment-author"]')).toContainText('developer@example.com');
  });

  test('should rollback deployment', async ({ page }) => {
    // Select previous successful deployment
    await page.click('[data-testid="deployment-item"]:has([data-testid="deployment-status"]:has-text("Success"))');
    
    // Click rollback button
    await page.click('[data-testid="rollback-button"]');
    
    // Confirm rollback
    await page.click('[data-testid="confirm-rollback"]');
    
    // Should show rollback in progress
    await expect(page.locator('[data-testid="deployment-status"]')).toContainText('Rolling back');
    
    // Should show rollback notification
    await expect(page.locator('[data-testid="notification-toast"]')).toContainText('Rollback initiated');
  });

  test('should configure deployment settings', async ({ page }) => {
    // Open deployment settings
    await page.click('[data-testid="deployment-settings"]');
    
    // Configure auto-deployment
    await page.check('[data-testid="enable-auto-deploy"]');
    await page.selectOption('[data-testid="auto-deploy-branch"]', 'main');
    await page.selectOption('[data-testid="auto-deploy-environment"]', 'staging');
    
    // Configure build settings
    await page.fill('[data-testid="build-command"]', 'npm run build');
    await page.fill('[data-testid="output-directory"]', 'dist');
    
    // Save settings
    await page.click('[data-testid="save-deployment-settings"]');
    
    // Should show success message
    await expect(page.locator('[data-testid="success-message"]')).toContainText('Deployment settings saved');
  });

  test('should show deployment metrics and analytics', async ({ page }) => {
    // Navigate to deployment analytics
    await page.click('[data-testid="deployment-analytics"]');
    
    // Should show deployment frequency chart
    await expect(page.locator('[data-testid="deployment-frequency-chart"]')).toBeVisible();
    
    // Should show success rate metrics
    await expect(page.locator('[data-testid="success-rate-metric"]')).toBeVisible();
    await expect(page.locator('[data-testid="success-rate-value"]')).toContainText('%');
    
    // Should show average deployment time
    await expect(page.locator('[data-testid="avg-deployment-time"]')).toBeVisible();
    
    // Should show deployment trends
    await expect(page.locator('[data-testid="deployment-trends"]')).toBeVisible();
  });
});