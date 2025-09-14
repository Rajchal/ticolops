import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DeploymentCard, type Deployment } from '../DeploymentCard';

const mockDeployment: Deployment = {
  id: '1',
  repositoryId: 'repo-1',
  repositoryName: 'test-repository',
  projectId: 'project-1',
  projectName: 'Test Project',
  branch: 'main',
  commitHash: 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0',
  commitMessage: 'Add new feature for testing',
  author: 'John Doe',
  status: 'success',
  url: 'https://test-repository.vercel.app',
  previewUrl: 'https://test-repository.vercel.app',
  buildDuration: 120,
  startedAt: new Date('2024-01-15T10:00:00Z'),
  completedAt: new Date('2024-01-15T10:02:00Z'),
  logs: [
    '[2024-01-15T10:00:00Z] [INFO] Starting build process...',
    '[2024-01-15T10:01:00Z] [INFO] Build completed successfully',
  ],
  buildCommand: 'npm run build',
  environment: 'production',
};

describe('DeploymentCard', () => {
  const mockOnViewLogs = vi.fn();
  const mockOnViewPreview = vi.fn();
  const mockOnRetry = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render deployment information correctly', () => {
    render(
      <DeploymentCard
        deployment={mockDeployment}
        onViewLogs={mockOnViewLogs}
        onViewPreview={mockOnViewPreview}
        onRetry={mockOnRetry}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('test-repository')).toBeInTheDocument();
    expect(screen.getByText('production')).toBeInTheDocument();
    expect(screen.getByText('Deployed')).toBeInTheDocument();
    expect(screen.getByText('Add new feature for testing')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('main')).toBeInTheDocument();
  });

  it('should display correct status styling for different statuses', () => {
    const { rerender } = render(
      <DeploymentCard deployment={mockDeployment} />
    );

    // Success status
    expect(screen.getByText('Deployed')).toHaveClass('text-green-600');

    // Failed status
    rerender(
      <DeploymentCard deployment={{ ...mockDeployment, status: 'failed' }} />
    );
    expect(screen.getByText('Failed')).toHaveClass('text-red-600');

    // Building status
    rerender(
      <DeploymentCard deployment={{ ...mockDeployment, status: 'building' }} />
    );
    expect(screen.getByText('Building')).toHaveClass('text-blue-600');

    // Pending status
    rerender(
      <DeploymentCard deployment={{ ...mockDeployment, status: 'pending' }} />
    );
    expect(screen.getByText('Pending')).toHaveClass('text-yellow-600');
  });

  it('should display correct environment styling', () => {
    const { rerender } = render(
      <DeploymentCard deployment={mockDeployment} />
    );

    // Production environment
    expect(screen.getByText('production')).toHaveClass('bg-red-100', 'text-red-800');

    // Staging environment
    rerender(
      <DeploymentCard deployment={{ ...mockDeployment, environment: 'staging' }} />
    );
    expect(screen.getByText('staging')).toHaveClass('bg-yellow-100', 'text-yellow-800');

    // Development environment
    rerender(
      <DeploymentCard deployment={{ ...mockDeployment, environment: 'development' }} />
    );
    expect(screen.getByText('development')).toHaveClass('bg-blue-100', 'text-blue-800');
  });

  it('should show preview button for successful deployments', () => {
    render(
      <DeploymentCard
        deployment={mockDeployment}
        onViewPreview={mockOnViewPreview}
      />
    );

    const previewButton = screen.getByText('Open Preview');
    expect(previewButton).toBeInTheDocument();

    fireEvent.click(previewButton);
    expect(mockOnViewPreview).toHaveBeenCalledWith(mockDeployment);
  });

  it('should not show preview button for failed deployments', () => {
    render(
      <DeploymentCard
        deployment={{ ...mockDeployment, status: 'failed', url: undefined }}
        onViewPreview={mockOnViewPreview}
      />
    );

    expect(screen.queryByText('Open Preview')).not.toBeInTheDocument();
  });

  it('should show error message for failed deployments', () => {
    const failedDeployment = {
      ...mockDeployment,
      status: 'failed' as const,
      errorMessage: 'Build failed due to missing dependencies',
    };

    render(<DeploymentCard deployment={failedDeployment} />);

    expect(screen.getByText('Deployment Failed')).toBeInTheDocument();
    expect(screen.getByText('Build failed due to missing dependencies')).toBeInTheDocument();
  });

  it('should show progress indicator for building deployments', () => {
    render(
      <DeploymentCard
        deployment={{ ...mockDeployment, status: 'building', completedAt: undefined }}
      />
    );

    expect(screen.getByText('Building...')).toBeInTheDocument();
    expect(screen.getByRole('progressbar') || screen.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('should call onViewLogs when View Logs button is clicked', () => {
    render(
      <DeploymentCard
        deployment={mockDeployment}
        onViewLogs={mockOnViewLogs}
      />
    );

    const logsButton = screen.getByText('View Logs');
    fireEvent.click(logsButton);

    expect(mockOnViewLogs).toHaveBeenCalledWith(mockDeployment);
  });

  it('should show retry button for failed deployments', () => {
    render(
      <DeploymentCard
        deployment={{ ...mockDeployment, status: 'failed' }}
        onRetry={mockOnRetry}
      />
    );

    const retryButton = screen.getByText('Retry');
    expect(retryButton).toBeInTheDocument();

    fireEvent.click(retryButton);
    expect(mockOnRetry).toHaveBeenCalledWith({ ...mockDeployment, status: 'failed' });
  });

  it('should show cancel button for building deployments', () => {
    render(
      <DeploymentCard
        deployment={{ ...mockDeployment, status: 'building' }}
        onCancel={mockOnCancel}
      />
    );

    const cancelButton = screen.getByText('Cancel');
    expect(cancelButton).toBeInTheDocument();

    fireEvent.click(cancelButton);
    expect(mockOnCancel).toHaveBeenCalledWith({ ...mockDeployment, status: 'building' });
  });

  it('should not show actions when showActions is false', () => {
    render(
      <DeploymentCard
        deployment={mockDeployment}
        showActions={false}
      />
    );

    expect(screen.queryByText('View Logs')).not.toBeInTheDocument();
    expect(screen.queryByText('Open Preview')).not.toBeInTheDocument();
  });

  it('should render in compact mode', () => {
    render(
      <DeploymentCard
        deployment={mockDeployment}
        compact={true}
      />
    );

    // In compact mode, should show less information
    expect(screen.getByText('test-repository')).toBeInTheDocument();
    expect(screen.getByText('Deployed')).toBeInTheDocument();
    expect(screen.queryByText('Add new feature for testing')).not.toBeInTheDocument(); // Commit message not shown in compact
  });

  it('should format build duration correctly', () => {
    render(<DeploymentCard deployment={mockDeployment} />);

    expect(screen.getByText('2m 0s')).toBeInTheDocument();
  });

  it('should format commit hash correctly', () => {
    render(<DeploymentCard deployment={mockDeployment} />);

    expect(screen.getByText('a1b2c3d')).toBeInTheDocument(); // First 7 characters
  });

  it('should show build command when available', () => {
    render(<DeploymentCard deployment={mockDeployment} />);

    expect(screen.getByText('npm run build')).toBeInTheDocument();
  });

  it('should handle missing optional fields gracefully', () => {
    const minimalDeployment = {
      ...mockDeployment,
      url: undefined,
      previewUrl: undefined,
      buildDuration: undefined,
      completedAt: undefined,
      buildCommand: undefined,
      errorMessage: undefined,
    };

    render(<DeploymentCard deployment={minimalDeployment} />);

    // Should still render basic information
    expect(screen.getByText('test-repository')).toBeInTheDocument();
    expect(screen.getByText('Deployed')).toBeInTheDocument();
  });

  it('should show spinning icon for building status', () => {
    render(
      <DeploymentCard
        deployment={{ ...mockDeployment, status: 'building' }}
      />
    );

    const spinningIcon = screen.getByText('Building').parentElement?.querySelector('.animate-spin');
    expect(spinningIcon).toBeInTheDocument();
  });

  it('should display timestamps correctly', () => {
    render(<DeploymentCard deployment={mockDeployment} />);

    // Should show formatted dates
    expect(screen.getByText(/1\/15\/2024/)).toBeInTheDocument();
  });
});