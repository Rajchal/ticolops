import { test, expect } from '@playwright/test';

test.describe('Project Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/');
    await page.fill('[data-testid="login-email"]', 'test@example.com');
    await page.fill('[data-testid="login-password"]', 'password123');
    await page.click('[data-testid="login-submit"]');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should create new project', async ({ page }) => {
    // Navigate to create project
    await page.click('[data-testid="create-project-button"]');
    
    // Fill project form
    await page.fill('[data-testid="project-name"]', 'Test Project');
    await page.fill('[data-testid="project-description"]', 'A test project for E2E testing');
    
    // Submit form
    await page.click('[data-testid="create-project-submit"]');
    
    // Should show project in list
    await expect(page.locator('[data-testid="project-list"]')).toContainText('Test Project');
    await expect(page.locator('[data-testid="project-description"]')).toContainText('A test project for E2E testing');
  });

  test('should invite team member to project', async ({ page }) => {
    // Navigate to project
    await page.click('[data-testid="project-card"]:has-text("Test Project")');
    
    // Open team management
    await page.click('[data-testid="manage-team-button"]');
    
    // Invite member
    await page.fill('[data-testid="invite-email"]', 'teammate@example.com');
    await page.selectOption('[data-testid="member-role"]', 'developer');
    await page.click('[data-testid="send-invite-button"]');
    
    // Should show pending invitation
    await expect(page.locator('[data-testid="pending-invitations"]')).toContainText('teammate@example.com');
    await expect(page.locator('[data-testid="invitation-status"]')).toContainText('Pending');
  });

  test('should connect repository to project', async ({ page }) => {
    // Navigate to project
    await page.click('[data-testid="project-card"]:has-text("Test Project")');
    
    // Open repository settings
    await page.click('[data-testid="repository-settings"]');
    
    // Connect repository
    await page.selectOption('[data-testid="git-provider"]', 'github');
    await page.fill('[data-testid="repository-url"]', 'https://github.com/user/test-repo');
    await page.fill('[data-testid="access-token"]', 'ghp_test_token_123');
    await page.click('[data-testid="connect-repository"]');
    
    // Should show connected repository
    await expect(page.locator('[data-testid="connected-repo"]')).toContainText('user/test-repo');
    await expect(page.locator('[data-testid="repo-status"]')).toContainText('Connected');
  });

  test('should update project settings', async ({ page }) => {
    // Navigate to project
    await page.click('[data-testid="project-card"]:has-text("Test Project")');
    
    // Open project settings
    await page.click('[data-testid="project-settings"]');
    
    // Update settings
    await page.fill('[data-testid="project-name"]', 'Updated Test Project');
    await page.check('[data-testid="enable-notifications"]');
    await page.selectOption('[data-testid="deployment-environment"]', 'staging');
    
    // Save changes
    await page.click('[data-testid="save-settings"]');
    
    // Should show success message
    await expect(page.locator('[data-testid="success-message"]')).toContainText('Project settings updated');
    
    // Verify changes
    await expect(page.locator('[data-testid="project-title"]')).toContainText('Updated Test Project');
  });

  test('should delete project', async ({ page }) => {
    // Navigate to project
    await page.click('[data-testid="project-card"]:has-text("Updated Test Project")');
    
    // Open project settings
    await page.click('[data-testid="project-settings"]');
    
    // Delete project
    await page.click('[data-testid="delete-project-button"]');
    
    // Confirm deletion
    await page.fill('[data-testid="confirm-project-name"]', 'Updated Test Project');
    await page.click('[data-testid="confirm-delete"]');
    
    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    
    // Project should not be in list
    await expect(page.locator('[data-testid="project-list"]')).not.toContainText('Updated Test Project');
  });
});