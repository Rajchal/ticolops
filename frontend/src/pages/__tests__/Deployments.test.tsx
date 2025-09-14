import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { Deployments } from '../Deployments';
import { AuthProvider } from '../../contexts/AuthContext';

// Mock the auth context
const mockUser = {
  id: 'user-1',
  email: 'test@example.com',
  name: 'Test User',
  role: 'student' as const,
};

vi.mock('../../contexts/AuthContext', async () => {
  const actual = await vi.importActual('../../contexts/AuthContext');
  return {
    ...actual,
    useAuth: () => ({
      user: mockUser,
      login: vi.fn(),
      logout: vi.fn(),
      register: vi.fn(),
      isLoading: false,
    }),
  };
});

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <BrowserRouter>
    <AuthProvider>
      {children}
    </AuthProvider>
  </BrowserRouter>
);

describe('Deployments Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock window.confirm
    Object.defineProperty(window, 'confirm', {
      writable: true,
      value: vi.fn(() => true),
    });
  });

  it('should render deployments page with header and stats', async () => {
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    expect(screen.getByText('Deployments')).toBeInTheDocument();
    expect(screen.getByText('Monitor your application deployments and preview live versions')).toBeInTheDocument();
    expect(screen.getByText('Refresh')).toBeInTheDocument();

    // Check stats cards
    expect(screen.getByText('Total Deployments')).toBeInTheDocument();
    expect(screen.getByText('Successful')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
  });

  it('should show search and filter controls', () => {
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    expect(screen.getByPlaceholderText('Search deployments...')).toBeInTheDocument();
    expect(screen.getByDisplayValue('All Status')).toBeInTheDocument();
    expect(screen.getByDisplayValue('All Environments')).toBeInTheDocument();
  });

  it('should display mock deployments', async () => {
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('ecommerce-frontend')).toBeInTheDocument();
      expect(screen.getByText('ecommerce-backend')).toBeInTheDocument();
      expect(screen.getByText('task-manager-app')).toBeInTheDocument();
      expect(screen.getByText('blog-platform')).toBeInTheDocument();
    });
  });

  it('should filter deployments by search query', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    const searchInput = screen.getByPlaceholderText('Search deployments...');
    await user.type(searchInput, 'ecommerce');

    await waitFor(() => {
      expect(screen.getByText('ecommerce-frontend')).toBeInTheDocument();
      expect(screen.getByText('ecommerce-backend')).toBeInTheDocument();
      expect(screen.queryByText('task-manager-app')).not.toBeInTheDocument();
    });
  });

  it('should filter deployments by status', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    const statusFilter = screen.getByDisplayValue('All Status');
    await user.selectOptions(statusFilter, 'success');

    await waitFor(() => {
      expect(screen.getByText('ecommerce-frontend')).toBeInTheDocument();
      expect(screen.queryByText('ecommerce-backend')).not.toBeInTheDocument(); // building
      expect(screen.queryByText('task-manager-app')).not.toBeInTheDocument(); // failed
    });
  });

  it('should filter deployments by environment', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    const environmentFilter = screen.getByDisplayValue('All Environments');
    await user.selectOptions(environmentFilter, 'production');

    await waitFor(() => {
      expect(screen.getByText('ecommerce-frontend')).toBeInTheDocument();
      expect(screen.getByText('task-manager-app')).toBeInTheDocument();
      expect(screen.queryByText('ecommerce-backend')).not.toBeInTheDocument(); // staging
    });
  });

  it('should refresh deployments when refresh button is clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    const refreshButton = screen.getByText('Refresh');
    await user.click(refreshButton);

    // Should show loading state
    expect(refreshButton).toBeDisabled();
  });

  it('should display correct stats', async () => {
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    await waitFor(() => {
      // Total deployments: 4
      expect(screen.getByText('4')).toBeInTheDocument();
      
      // Successful: 1 (ecommerce-frontend)
      expect(screen.getByText('1')).toBeInTheDocument();
      
      // Failed: 1 (task-manager-app)
      expect(screen.getByText('1')).toBeInTheDocument();
      
      // In Progress: 2 (ecommerce-backend building, blog-platform pending)
      expect(screen.getByText('2')).toBeInTheDocument();
    });
  });

  it('should open logs modal when View Logs is clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('ecommerce-frontend')).toBeInTheDocument();
    });

    // Find and click View Logs button
    const viewLogsButtons = screen.getAllByText('View Logs');
    await user.click(viewLogsButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Deployment Logs')).toBeInTheDocument();
    });
  });

  it('should open preview modal when preview is clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('ecommerce-frontend')).toBeInTheDocument();
    });

    // Find and click Open Preview button (only available for successful deployments)
    const previewButtons = screen.getAllByText('Open Preview');
    await user.click(previewButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Preview')).toBeInTheDocument();
    });
  });

  it('should retry failed deployment', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('task-manager-app')).toBeInTheDocument();
    });

    // Find and click Retry button (only available for failed deployments)
    const retryButtons = screen.getAllByText('Retry');
    await user.click(retryButtons[0]);

    // Deployment status should change to pending
    await waitFor(() => {
      // The deployment should now show as pending
      expect(screen.getByText('Pending')).toBeInTheDocument();
    });
  });

  it('should cancel building deployment', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('ecommerce-backend')).toBeInTheDocument();
    });

    // Find and click Cancel button (only available for building deployments)
    const cancelButtons = screen.getAllByText('Cancel');
    await user.click(cancelButtons[0]);

    // Should show confirmation dialog
    expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to cancel this deployment?');

    // Deployment status should change to cancelled
    await waitFor(() => {
      expect(screen.getByText('Cancelled')).toBeInTheDocument();
    });
  });

  it('should show empty state when no deployments match filters', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    const searchInput = screen.getByPlaceholderText('Search deployments...');
    await user.type(searchInput, 'nonexistent');

    await waitFor(() => {
      expect(screen.getByText('No deployments found')).toBeInTheDocument();
      expect(screen.getByText('Try adjusting your search or filters')).toBeInTheDocument();
    });
  });

  it('should display deployment cards with correct information', async () => {
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    await waitFor(() => {
      // Check successful deployment
      expect(screen.getByText('ecommerce-frontend')).toBeInTheDocument();
      expect(screen.getByText('Deployed')).toBeInTheDocument();
      expect(screen.getByText('production')).toBeInTheDocument();

      // Check building deployment
      expect(screen.getByText('ecommerce-backend')).toBeInTheDocument();
      expect(screen.getByText('Building')).toBeInTheDocument();
      expect(screen.getByText('staging')).toBeInTheDocument();

      // Check failed deployment
      expect(screen.getByText('task-manager-app')).toBeInTheDocument();
      expect(screen.getByText('Failed')).toBeInTheDocument();

      // Check pending deployment
      expect(screen.getByText('blog-platform')).toBeInTheDocument();
      expect(screen.getByText('Pending')).toBeInTheDocument();
      expect(screen.getByText('development')).toBeInTheDocument();
    });
  });

  it('should handle multiple filter combinations', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    // Apply both search and status filter
    const searchInput = screen.getByPlaceholderText('Search deployments...');
    await user.type(searchInput, 'ecommerce');

    const statusFilter = screen.getByDisplayValue('All Status');
    await user.selectOptions(statusFilter, 'success');

    await waitFor(() => {
      expect(screen.getByText('ecommerce-frontend')).toBeInTheDocument();
      expect(screen.queryByText('ecommerce-backend')).not.toBeInTheDocument();
      expect(screen.queryByText('task-manager-app')).not.toBeInTheDocument();
      expect(screen.queryByText('blog-platform')).not.toBeInTheDocument();
    });
  });

  it('should close modals when close buttons are clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    // Open logs modal
    await waitFor(() => {
      expect(screen.getByText('ecommerce-frontend')).toBeInTheDocument();
    });

    const viewLogsButtons = screen.getAllByText('View Logs');
    await user.click(viewLogsButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Deployment Logs')).toBeInTheDocument();
    });

    // Close logs modal
    const closeButton = screen.getByRole('button', { name: /close/i });
    await user.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText('Deployment Logs')).not.toBeInTheDocument();
    });
  });

  it('should show correct deployment counts in stats', async () => {
    render(
      <TestWrapper>
        <Deployments />
      </TestWrapper>
    );

    await waitFor(() => {
      // Should show correct counts based on mock data
      const totalCard = screen.getByText('Total Deployments').parentElement;
      expect(totalCard?.querySelector('.text-2xl')).toHaveTextContent('4');

      const successfulCard = screen.getByText('Successful').parentElement;
      expect(successfulCard?.querySelector('.text-2xl')).toHaveTextContent('1');

      const failedCard = screen.getByText('Failed').parentElement;
      expect(failedCard?.querySelector('.text-2xl')).toHaveTextContent('1');

      const inProgressCard = screen.getByText('In Progress').parentElement;
      expect(inProgressCard?.querySelector('.text-2xl')).toHaveTextContent('2');
    });
  });
});