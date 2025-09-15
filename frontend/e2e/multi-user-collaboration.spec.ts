import { test, expect } from '@playwright/test';

test.describe('Multi-User Collaboration Scenarios', () => {
  test('should handle multiple users working on same project', async ({ browser }) => {
    // Create two browser contexts for different users
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();
    
    const user1Page = await context1.newPage();
    const user2Page = await context2.newPage();
    
    // Login User 1
    await user1Page.goto('/');
    await user1Page.fill('[data-testid="login-email"]', 'user1@example.com');
    await user1Page.fill('[data-testid="login-password"]', 'password123');
    await user1Page.click('[data-testid="login-submit"]');
    await expect(user1Page).toHaveURL(/\/dashboard/);
    
    // Login User 2
    await user2Page.goto('/');
    await user2Page.fill('[data-testid="login-email"]', 'user2@example.com');
    await user2Page.fill('[data-testid="login-password"]', 'password123');
    await user2Page.click('[data-testid="login-submit"]');
    await expect(user2Page).toHaveURL(/\/dashboard/);
    
    // Both users navigate to same project
    await user1Page.click('[data-testid="project-card"]:first');
    await user2Page.click('[data-testid="project-card"]:first');
    
    // User 1 should see User 2 in team presence
    await expect(user1Page.locator('[data-testid="team-presence"]')).toContainText('user2@example.com');
    
    // User 2 should see User 1 in team presence
    await expect(user2Page.locator('[data-testid="team-presence"]')).toContainText('user1@example.com');
    
    // User 1 navigates to repository tab
    await user1Page.click('[data-testid="repository-tab"]');
    
    // User 2 should see User 1's activity update
    await expect(user2Page.locator('[data-testid="activity-feed"]')).toContainText('user1@example.com is viewing Repository');
    
    // User 2 navigates to deployments tab
    await user2Page.click('[data-testid="deployments-tab"]');
    
    // User 1 should see User 2's activity update
    await expect(user1Page.locator('[data-testid="activity-feed"]')).toContainText('user2@example.com is viewing Deployments');
    
    // Clean up
    await context1.close();
    await context2.close();
  });

  test('should detect and resolve conflicts between users', async ({ browser }) => {
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();
    
    const user1Page = await context1.newPage();
    const user2Page = await context2.newPage();
    
    // Setup both users in same project
    await Promise.all([
      setupUser(user1Page, 'user1@example.com'),
      setupUser(user2Page, 'user2@example.com')
    ]);
    
    // Both users start working on same file
    await user1Page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('user-activity', {
        detail: {
          location: 'src/components/Header.tsx',
          action: 'editing'
        }
      }));
    });
    
    await user2Page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('user-activity', {
        detail: {
          location: 'src/components/Header.tsx',
          action: 'editing'
        }
      }));
    });
    
    // Both users should see conflict notification
    await expect(user1Page.locator('[data-testid="conflict-notification"]')).toBeVisible();
    await expect(user2Page.locator('[data-testid="conflict-notification"]')).toBeVisible();
    
    // User 1 resolves conflict by moving to different file
    await user1Page.click('[data-testid="resolve-conflict"]');
    await user1Page.click('[data-testid="work-on-different-file"]');
    
    // Conflict should be resolved for both users
    await expect(user1Page.locator('[data-testid="conflict-notification"]')).not.toBeVisible();
    await expect(user2Page.locator('[data-testid="conflict-notification"]')).not.toBeVisible();
    
    await context1.close();
    await context2.close();
  });

  test('should handle real-time notifications between users', async ({ browser }) => {
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();
    
    const user1Page = await context1.newPage();
    const user2Page = await context2.newPage();
    
    await Promise.all([
      setupUser(user1Page, 'user1@example.com'),
      setupUser(user2Page, 'user2@example.com')
    ]);
    
    // User 1 triggers a deployment
    await user1Page.click('[data-testid="deployments-tab"]');
    await user1Page.click('[data-testid="deploy-button"]');
    await user1Page.click('[data-testid="confirm-deploy"]');
    
    // User 2 should receive deployment notification
    await expect(user2Page.locator('[data-testid="notification-toast"]')).toContainText('Deployment started by user1@example.com');
    
    // Simulate deployment completion
    await user1Page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('websocket-message', {
        detail: {
          type: 'deployment_status',
          payload: {
            status: 'success',
            url: 'https://staging.example.com',
            triggeredBy: 'user1@example.com'
          }
        }
      }));
    });
    
    // User 2 should receive success notification
    await expect(user2Page.locator('[data-testid="notification-toast"]')).toContainText('Deployment successful');
    
    await context1.close();
    await context2.close();
  });

  test('should handle user mentions and direct communication', async ({ browser }) => {
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();
    
    const user1Page = await context1.newPage();
    const user2Page = await context2.newPage();
    
    await Promise.all([
      setupUser(user1Page, 'user1@example.com'),
      setupUser(user2Page, 'user2@example.com')
    ]);
    
    // User 1 mentions User 2 in a comment
    await user1Page.click('[data-testid="add-comment-button"]');
    await user1Page.fill('[data-testid="comment-input"]', 'Hey @user2@example.com, can you review this deployment?');
    await user1Page.click('[data-testid="submit-comment"]');
    
    // User 2 should receive mention notification
    await expect(user2Page.locator('[data-testid="notification-toast"]')).toContainText('You were mentioned by user1@example.com');
    await expect(user2Page.locator('[data-testid="mention-notification"]')).toBeVisible();
    
    // User 2 clicks on mention notification
    await user2Page.click('[data-testid="mention-notification"]');
    
    // Should navigate to the comment location
    await expect(user2Page.locator('[data-testid="highlighted-comment"]')).toContainText('Hey @user2@example.com');
    
    // User 2 replies to the comment
    await user2Page.click('[data-testid="reply-button"]');
    await user2Page.fill('[data-testid="reply-input"]', 'Sure, I\'ll review it now!');
    await user2Page.click('[data-testid="submit-reply"]');
    
    // User 1 should receive reply notification
    await expect(user1Page.locator('[data-testid="notification-toast"]')).toContainText('user2@example.com replied to your comment');
    
    await context1.close();
    await context2.close();
  });

  test('should handle collaborative editing sessions', async ({ browser }) => {
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();
    
    const user1Page = await context1.newPage();
    const user2Page = await context2.newPage();
    
    await Promise.all([
      setupUser(user1Page, 'user1@example.com'),
      setupUser(user2Page, 'user2@example.com')
    ]);
    
    // User 1 starts collaborative editing session
    await user1Page.click('[data-testid="repository-tab"]');
    await user1Page.click('[data-testid="file-item"]:has-text("config.json")');
    await user1Page.click('[data-testid="start-collaboration"]');
    
    // User 2 should receive collaboration invitation
    await expect(user2Page.locator('[data-testid="collaboration-invite"]')).toBeVisible();
    await expect(user2Page.locator('[data-testid="invite-message"]')).toContainText('user1@example.com invited you to collaborate on config.json');
    
    // User 2 accepts invitation
    await user2Page.click('[data-testid="accept-collaboration"]');
    
    // Both users should see collaborative editor
    await expect(user1Page.locator('[data-testid="collaborative-editor"]')).toBeVisible();
    await expect(user2Page.locator('[data-testid="collaborative-editor"]')).toBeVisible();
    
    // User 1 makes changes
    await user1Page.fill('[data-testid="editor-content"]', '{\n  "version": "2.0",\n  "updated_by": "user1"\n}');
    
    // User 2 should see changes in real-time
    await expect(user2Page.locator('[data-testid="editor-content"]')).toContainText('"updated_by": "user1"');
    
    // User 2 makes additional changes
    await user2Page.evaluate(() => {
      const editor = document.querySelector('[data-testid="editor-content"]');
      editor.value = editor.value.replace('"updated_by": "user1"', '"updated_by": "user1",\n  "reviewed_by": "user2"');
      editor.dispatchEvent(new Event('input'));
    });
    
    // User 1 should see User 2's changes
    await expect(user1Page.locator('[data-testid="editor-content"]')).toContainText('"reviewed_by": "user2"');
    
    // Show cursor positions
    await expect(user1Page.locator('[data-testid="user-cursor"]:has-text("user2@example.com")')).toBeVisible();
    await expect(user2Page.locator('[data-testid="user-cursor"]:has-text("user1@example.com")')).toBeVisible();
    
    await context1.close();
    await context2.close();
  });

  test('should handle team permission and role changes', async ({ browser }) => {
    const context1 = await browser.newContext(); // Admin user
    const context2 = await browser.newContext(); // Regular user
    
    const adminPage = await context1.newPage();
    const userPage = await context2.newPage();
    
    // Setup admin user
    await adminPage.goto('/');
    await adminPage.fill('[data-testid="login-email"]', 'admin@example.com');
    await adminPage.fill('[data-testid="login-password"]', 'password123');
    await adminPage.click('[data-testid="login-submit"]');
    await adminPage.click('[data-testid="project-card"]:first');
    
    // Setup regular user
    await userPage.goto('/');
    await userPage.fill('[data-testid="login-email"]', 'user@example.com');
    await userPage.fill('[data-testid="login-password"]', 'password123');
    await userPage.click('[data-testid="login-submit"]');
    await userPage.click('[data-testid="project-card"]:first');
    
    // Regular user should not see admin controls
    await expect(userPage.locator('[data-testid="project-settings"]')).not.toBeVisible();
    await expect(userPage.locator('[data-testid="manage-team-button"]')).not.toBeVisible();
    
    // Admin promotes user to maintainer
    await adminPage.click('[data-testid="manage-team-button"]');
    await adminPage.click('[data-testid="user-role-dropdown"]:has-text("user@example.com")');
    await adminPage.selectOption('[data-testid="role-select"]', 'maintainer');
    await adminPage.click('[data-testid="update-role"]');
    
    // User should receive role change notification
    await expect(userPage.locator('[data-testid="notification-toast"]')).toContainText('Your role has been updated to maintainer');
    
    // User should now see maintainer controls
    await userPage.reload();
    await expect(userPage.locator('[data-testid="manage-team-button"]')).toBeVisible();
    await expect(userPage.locator('[data-testid="deployment-settings"]')).toBeVisible();
    
    // But still not see admin-only controls
    await expect(userPage.locator('[data-testid="delete-project-button"]')).not.toBeVisible();
    
    await context1.close();
    await context2.close();
  });

  // Helper function to setup user
  async function setupUser(page, email) {
    await page.goto('/');
    await page.fill('[data-testid="login-email"]', email);
    await page.fill('[data-testid="login-password"]', 'password123');
    await page.click('[data-testid="login-submit"]');
    await expect(page).toHaveURL(/\/dashboard/);
    await page.click('[data-testid="project-card"]:first');
  }
});