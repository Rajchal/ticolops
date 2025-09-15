import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display login page', async ({ page }) => {
    await expect(page).toHaveTitle(/Ticolops/);
    await expect(page.locator('h1')).toContainText('Welcome to Ticolops');
  });

  test('should register new user successfully', async ({ page }) => {
    // Navigate to register page
    await page.click('text=Sign Up');
    
    // Fill registration form
    await page.fill('[data-testid="register-name"]', 'Test User');
    await page.fill('[data-testid="register-email"]', 'test@example.com');
    await page.fill('[data-testid="register-password"]', 'password123');
    await page.fill('[data-testid="register-confirm-password"]', 'password123');
    
    // Submit form
    await page.click('[data-testid="register-submit"]');
    
    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator('[data-testid="user-name"]')).toContainText('Test User');
  });

  test('should login existing user successfully', async ({ page }) => {
    // Fill login form
    await page.fill('[data-testid="login-email"]', 'test@example.com');
    await page.fill('[data-testid="login-password"]', 'password123');
    
    // Submit form
    await page.click('[data-testid="login-submit"]');
    
    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator('[data-testid="user-name"]')).toContainText('Test User');
  });

  test('should show error for invalid credentials', async ({ page }) => {
    // Fill login form with invalid credentials
    await page.fill('[data-testid="login-email"]', 'invalid@example.com');
    await page.fill('[data-testid="login-password"]', 'wrongpassword');
    
    // Submit form
    await page.click('[data-testid="login-submit"]');
    
    // Should show error message
    await expect(page.locator('[data-testid="error-message"]')).toContainText('Invalid credentials');
  });

  test('should logout user successfully', async ({ page }) => {
    // Login first
    await page.fill('[data-testid="login-email"]', 'test@example.com');
    await page.fill('[data-testid="login-password"]', 'password123');
    await page.click('[data-testid="login-submit"]');
    
    // Wait for dashboard
    await expect(page).toHaveURL(/\/dashboard/);
    
    // Logout
    await page.click('[data-testid="user-menu"]');
    await page.click('[data-testid="logout-button"]');
    
    // Should redirect to login page
    await expect(page).toHaveURL('/');
    await expect(page.locator('h1')).toContainText('Welcome to Ticolops');
  });
});