import { test, expect } from '@playwright/test';

test.describe('Performance Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/');
    await page.fill('[data-testid="login-email"]', 'test@example.com');
    await page.fill('[data-testid="login-password"]', 'password123');
    await page.click('[data-testid="login-submit"]');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should load dashboard within performance budget', async ({ page }) => {
    const startTime = Date.now();
    
    // Navigate to dashboard
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    
    const loadTime = Date.now() - startTime;
    
    // Should load within 3 seconds
    expect(loadTime).toBeLessThan(3000);
    
    // Check Core Web Vitals
    const metrics = await page.evaluate(() => {
      return new Promise((resolve) => {
        new PerformanceObserver((list) => {
          const entries = list.getEntries();
          const metrics = {};
          
          entries.forEach((entry) => {
            if (entry.entryType === 'navigation') {
              metrics.loadTime = entry.loadEventEnd - entry.loadEventStart;
              metrics.domContentLoaded = entry.domContentLoadedEventEnd - entry.domContentLoadedEventStart;
            }
            if (entry.entryType === 'largest-contentful-paint') {
              metrics.lcp = entry.startTime;
            }
            if (entry.entryType === 'first-input') {
              metrics.fid = entry.processingStart - entry.startTime;
            }
          });
          
          resolve(metrics);
        }).observe({ entryTypes: ['navigation', 'largest-contentful-paint', 'first-input'] });
      });
    });
    
    // LCP should be under 2.5 seconds
    if (metrics.lcp) {
      expect(metrics.lcp).toBeLessThan(2500);
    }
    
    // FID should be under 100ms
    if (metrics.fid) {
      expect(metrics.fid).toBeLessThan(100);
    }
  });

  test('should handle WebSocket connection performance', async ({ page }) => {
    // Navigate to project with real-time features
    await page.click('[data-testid="project-card"]:first');
    
    // Measure WebSocket connection time
    const connectionStart = Date.now();
    
    // Wait for WebSocket connection
    await page.waitForFunction(() => {
      return window.WebSocket && window.WebSocket.OPEN === 1;
    });
    
    const connectionTime = Date.now() - connectionStart;
    
    // WebSocket should connect within 1 second
    expect(connectionTime).toBeLessThan(1000);
    
    // Test message throughput
    const messageCount = 100;
    const messagesReceived = [];
    
    // Listen for WebSocket messages
    await page.evaluate((count) => {
      window.testMessages = [];
      const originalWebSocket = window.WebSocket;
      
      window.WebSocket = function(url, protocols) {
        const ws = new originalWebSocket(url, protocols);
        
        ws.addEventListener('message', (event) => {
          if (event.data.includes('test-message')) {
            window.testMessages.push(Date.now());
          }
        });
        
        return ws;
      };
    }, messageCount);
    
    // Send test messages
    const sendStart = Date.now();
    
    await page.evaluate((count) => {
      for (let i = 0; i < count; i++) {
        window.dispatchEvent(new CustomEvent('websocket-send', {
          detail: { type: 'test-message', id: i }
        }));
      }
    }, messageCount);
    
    // Wait for all messages to be processed
    await page.waitForFunction((count) => {
      return window.testMessages && window.testMessages.length >= count;
    }, messageCount);
    
    const totalTime = Date.now() - sendStart;
    const throughput = messageCount / (totalTime / 1000); // messages per second
    
    // Should handle at least 50 messages per second
    expect(throughput).toBeGreaterThan(50);
  });

  test('should handle large dataset rendering performance', async ({ page }) => {
    // Navigate to deployment history with large dataset
    await page.click('[data-testid="project-card"]:first');
    await page.click('[data-testid="deployments-tab"]');
    
    // Simulate large dataset
    await page.evaluate(() => {
      const largeDataset = Array.from({ length: 1000 }, (_, i) => ({
        id: `deploy-${i}`,
        status: i % 3 === 0 ? 'success' : i % 3 === 1 ? 'failed' : 'pending',
        branch: `feature-${i}`,
        commit: `commit-${i}`,
        timestamp: new Date(Date.now() - i * 60000).toISOString()
      }));
      
      window.dispatchEvent(new CustomEvent('load-deployments', {
        detail: { deployments: largeDataset }
      }));
    });
    
    const renderStart = Date.now();
    
    // Wait for list to render
    await page.waitForSelector('[data-testid="deployment-list"]');
    await page.waitForFunction(() => {
      const items = document.querySelectorAll('[data-testid="deployment-item"]');
      return items.length > 0;
    });
    
    const renderTime = Date.now() - renderStart;
    
    // Should render within 2 seconds
    expect(renderTime).toBeLessThan(2000);
    
    // Test scrolling performance
    const scrollStart = Date.now();
    
    // Scroll through the list
    for (let i = 0; i < 10; i++) {
      await page.mouse.wheel(0, 500);
      await page.waitForTimeout(50);
    }
    
    const scrollTime = Date.now() - scrollStart;
    
    // Scrolling should be smooth (under 1 second for 10 scrolls)
    expect(scrollTime).toBeLessThan(1000);
  });

  test('should handle concurrent user simulation', async ({ page, context }) => {
    // Create multiple pages to simulate concurrent users
    const pages = await Promise.all([
      context.newPage(),
      context.newPage(),
      context.newPage()
    ]);
    
    // Login all users concurrently
    const loginPromises = pages.map(async (userPage, index) => {
      await userPage.goto('/');
      await userPage.fill('[data-testid="login-email"]', `user${index}@example.com`);
      await userPage.fill('[data-testid="login-password"]', 'password123');
      await userPage.click('[data-testid="login-submit"]');
      return userPage.waitForURL(/\/dashboard/);
    });
    
    const loginStart = Date.now();
    await Promise.all(loginPromises);
    const loginTime = Date.now() - loginStart;
    
    // All users should login within 5 seconds
    expect(loginTime).toBeLessThan(5000);
    
    // Simulate concurrent activity
    const activityPromises = pages.map(async (userPage, index) => {
      await userPage.click('[data-testid="project-card"]:first');
      
      // Simulate different activities
      switch (index) {
        case 0:
          await userPage.click('[data-testid="repository-tab"]');
          break;
        case 1:
          await userPage.click('[data-testid="deployments-tab"]');
          break;
        case 2:
          await userPage.click('[data-testid="team-tab"]');
          break;
      }
      
      return userPage.waitForLoadState('networkidle');
    });
    
    const activityStart = Date.now();
    await Promise.all(activityPromises);
    const activityTime = Date.now() - activityStart;
    
    // Concurrent activities should complete within 3 seconds
    expect(activityTime).toBeLessThan(3000);
    
    // Clean up
    await Promise.all(pages.map(p => p.close()));
  });

  test('should handle memory usage efficiently', async ({ page }) => {
    // Navigate to project
    await page.click('[data-testid="project-card"]:first');
    
    // Get initial memory usage
    const initialMemory = await page.evaluate(() => {
      return performance.memory ? {
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit
      } : null;
    });
    
    if (!initialMemory) {
      test.skip('Performance.memory API not available');
      return;
    }
    
    // Simulate heavy operations
    for (let i = 0; i < 10; i++) {
      // Navigate between tabs
      await page.click('[data-testid="repository-tab"]');
      await page.waitForTimeout(100);
      await page.click('[data-testid="deployments-tab"]');
      await page.waitForTimeout(100);
      await page.click('[data-testid="team-tab"]');
      await page.waitForTimeout(100);
      
      // Trigger WebSocket messages
      await page.evaluate(() => {
        for (let j = 0; j < 10; j++) {
          window.dispatchEvent(new CustomEvent('websocket-message', {
            detail: {
              type: 'activity_update',
              payload: { user: 'test', action: 'navigate', timestamp: Date.now() }
            }
          }));
        }
      });
    }
    
    // Force garbage collection if available
    await page.evaluate(() => {
      if (window.gc) {
        window.gc();
      }
    });
    
    // Get final memory usage
    const finalMemory = await page.evaluate(() => {
      return {
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit
      };
    });
    
    // Memory usage should not increase by more than 50MB
    const memoryIncrease = finalMemory.used - initialMemory.used;
    expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024); // 50MB
    
    // Memory usage should not exceed 80% of the limit
    const memoryUsagePercentage = (finalMemory.used / finalMemory.limit) * 100;
    expect(memoryUsagePercentage).toBeLessThan(80);
  });

  test('should handle API response times', async ({ page }) => {
    // Intercept API calls and measure response times
    const apiTimes = [];
    
    page.on('response', (response) => {
      if (response.url().includes('/api/')) {
        const timing = response.timing();
        if (timing) {
          apiTimes.push({
            url: response.url(),
            status: response.status(),
            responseTime: timing.responseEnd - timing.requestStart
          });
        }
      }
    });
    
    // Navigate through different sections to trigger API calls
    await page.click('[data-testid="project-card"]:first');
    await page.waitForLoadState('networkidle');
    
    await page.click('[data-testid="repository-tab"]');
    await page.waitForLoadState('networkidle');
    
    await page.click('[data-testid="deployments-tab"]');
    await page.waitForLoadState('networkidle');
    
    await page.click('[data-testid="team-tab"]');
    await page.waitForLoadState('networkidle');
    
    // Analyze API response times
    const successfulRequests = apiTimes.filter(api => api.status < 400);
    
    if (successfulRequests.length > 0) {
      const averageResponseTime = successfulRequests.reduce((sum, api) => sum + api.responseTime, 0) / successfulRequests.length;
      const maxResponseTime = Math.max(...successfulRequests.map(api => api.responseTime));
      
      // Average API response time should be under 500ms
      expect(averageResponseTime).toBeLessThan(500);
      
      // No single API call should take more than 2 seconds
      expect(maxResponseTime).toBeLessThan(2000);
      
      // At least 95% of requests should be under 1 second
      const fastRequests = successfulRequests.filter(api => api.responseTime < 1000);
      const fastRequestPercentage = (fastRequests.length / successfulRequests.length) * 100;
      expect(fastRequestPercentage).toBeGreaterThan(95);
    }
  });
});