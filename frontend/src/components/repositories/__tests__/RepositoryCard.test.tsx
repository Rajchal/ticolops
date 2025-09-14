import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RepositoryCard, type Repository } from '../RepositoryCard';

const mockRepository: Repository = {
  id: '1',
  name: 'test-repository',
  url: 'https://github.com/user/test-repository',
  provider: 'github',
  branch: 'main',
  projectId: 'project-1',
  projectName: 'Test Project',
  isConnected: true,
  lastSync: new Date('2024-01-15T10:00:00Z'),
  deploymentUrl: 'https://test-repository.vercel.app',
  deploymentStatus: 'success',
  visibility: 'private',
  language: 'TypeScript',
  description: 'A test repository for unit testing',
  webhookConfigured: true,
  autoDeployEnabled: true,
};

describe('RepositoryCard', () => {
  const mockOnDisconnect = vi.fn();
  const mockOnConfigure = vi.fn();
  const mockOnSync = vi.fn();
  const mockOnViewDeployment = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock window.open
    Object.defineProperty(window, 'open', {
      writable: true,
      value: vi.fn(),
    });
  });

  it('should render repository information correctly', () => {
    render(
      <RepositoryCard
        repository={mockRepository}
        onDisconnect={mockOnDisconnect}
        onConfigure={mockOnConfigure}
        onSync={mockOnSync}
        onViewDeployment={mockOnViewDeployment}
      />
    );

    expect(screen.getByText('test-repository')).toBeInTheDocument();
    expect(screen.getByText('A test repository for unit testing')).toBeInTheDocument();
    expect(screen.getByText('Connected')).toBeInTheDocument();
    expect(screen.getByText('Github')).toBeInTheDocument();
    expect(screen.getByText('main')).toBeInTheDocument();
    expect(screen.getByText('TypeScript')).toBeInTheDocument();
    expect(screen.getByText('Project: Test Project')).toBeInTheDocument();
  });

  it('should display correct provider icons', () => {
    const { rerender } = render(
      <RepositoryCard repository={mockRepository} />
    );

    // GitHub
    expect(screen.getByText('🐙')).toBeInTheDocument();

    // GitLab
    rerender(
      <RepositoryCard repository={{ ...mockRepository, provider: 'gitlab' }} />
    );
    expect(screen.getByText('🦊')).toBeInTheDocument();

    // Bitbucket
    rerender(
      <RepositoryCard repository={{ ...mockRepository, provider: 'bitbucket' }} />
    );
    expect(screen.getByText('🪣')).toBeInTheDocument();
  });

  it('should display correct connection status', () => {
    const { rerender } = render(
      <RepositoryCard repository={mockRepository} />
    );

    // Connected
    expect(screen.getByText('Connected')).toHaveClass('bg-green-100', 'text-green-800');

    // Disconnected
    rerender(
      <RepositoryCard repository={{ ...mockRepository, isConnected: false }} />
    );
    expect(screen.getByText('Disconnected')).toHaveClass('bg-red-100', 'text-red-800');
  });

  it('should display correct deployment status', () => {
    const { rerender } = render(
      <RepositoryCard repository={mockRepository} />
    );

    // Success
    expect(screen.getByText('Deployed')).toHaveClass('text-green-600', 'bg-green-100');

    // Failed
    rerender(
      <RepositoryCard repository={{ ...mockRepository, deploymentStatus: 'failed' }} />
    );
    expect(screen.getByText('Failed')).toHaveClass('text-red-600', 'bg-red-100');

    // Building
    rerender(
      <RepositoryCard repository={{ ...mockRepository, deploymentStatus: 'building' }} />
    );
    expect(screen.getByText('Building')).toHaveClass('text-blue-600', 'bg-blue-100');

    // Pending
    rerender(
      <RepositoryCard repository={{ ...mockRepository, deploymentStatus: 'pending' }} />
    );
    expect(screen.getByText('Pending')).toHaveClass('text-yellow-600', 'bg-yellow-100');
  });

  it('should show View Live button for successful deployments', () => {
    render(
      <RepositoryCard
        repository={mockRepository}
        onViewDeployment={mockOnViewDeployment}
      />
    );

    const viewLiveButton = screen.getByText('View Live');
    expect(viewLiveButton).toBeInTheDocument();

    fireEvent.click(viewLiveButton);
    expect(mockOnViewDeployment).toHaveBeenCalledWith(mockRepository);
  });

  it('should not show View Live button for failed deployments', () => {
    render(
      <RepositoryCard
        repository={{ ...mockRepository, deploymentStatus: 'failed' }}
        onViewDeployment={mockOnViewDeployment}
      />
    );

    expect(screen.queryByText('View Live')).not.toBeInTheDocument();
  });

  it('should display webhook and auto-deploy configuration status', () => {
    render(<RepositoryCard repository={mockRepository} />);

    // Webhook configured
    expect(screen.getByText('Configured')).toBeInTheDocument();
    
    // Auto deploy enabled
    expect(screen.getByText('Enabled')).toBeInTheDocument();
  });

  it('should display correct configuration status icons', () => {
    const { rerender } = render(
      <RepositoryCard repository={mockRepository} />
    );

    // Webhook configured - should show check icon
    expect(screen.getByText('Configured')).toBeInTheDocument();

    // Webhook not configured
    rerender(
      <RepositoryCard repository={{ ...mockRepository, webhookConfigured: false }} />
    );
    expect(screen.getByText('Not configured')).toBeInTheDocument();

    // Auto deploy disabled
    rerender(
      <RepositoryCard repository={{ ...mockRepository, autoDeployEnabled: false }} />
    );
    expect(screen.getByText('Disabled')).toBeInTheDocument();
  });

  it('should call onSync when Sync button is clicked', () => {
    render(
      <RepositoryCard
        repository={mockRepository}
        onSync={mockOnSync}
      />
    );

    const syncButton = screen.getByText('Sync');
    fireEvent.click(syncButton);

    expect(mockOnSync).toHaveBeenCalledWith(mockRepository);
  });

  it('should disable Sync button when repository is disconnected', () => {
    render(
      <RepositoryCard
        repository={{ ...mockRepository, isConnected: false }}
        onSync={mockOnSync}
      />
    );

    const syncButton = screen.getByText('Sync');
    expect(syncButton).toBeDisabled();
  });

  it('should call onConfigure when Configure button is clicked', () => {
    render(
      <RepositoryCard
        repository={mockRepository}
        onConfigure={mockOnConfigure}
      />
    );

    const configureButton = screen.getByText('Configure');
    fireEvent.click(configureButton);

    expect(mockOnConfigure).toHaveBeenCalledWith(mockRepository);
  });

  it('should open repository URL when View on Provider button is clicked', () => {
    render(<RepositoryCard repository={mockRepository} />);

    const viewButton = screen.getByText('View on Github');
    fireEvent.click(viewButton);

    expect(window.open).toHaveBeenCalledWith(mockRepository.url, '_blank');
  });

  it('should call onDisconnect when Disconnect Repository button is clicked', () => {
    render(
      <RepositoryCard
        repository={mockRepository}
        onDisconnect={mockOnDisconnect}
      />
    );

    const disconnectButton = screen.getByText('Disconnect Repository');
    fireEvent.click(disconnectButton);

    expect(mockOnDisconnect).toHaveBeenCalledWith(mockRepository);
  });

  it('should not show actions when showActions is false', () => {
    render(
      <RepositoryCard
        repository={mockRepository}
        showActions={false}
      />
    );

    expect(screen.queryByText('Sync')).not.toBeInTheDocument();
    expect(screen.queryByText('Configure')).not.toBeInTheDocument();
    expect(screen.queryByText('View on Github')).not.toBeInTheDocument();
    expect(screen.queryByText('Disconnect Repository')).not.toBeInTheDocument();
  });

  it('should display visibility indicators correctly', () => {
    const { rerender } = render(
      <RepositoryCard repository={mockRepository} />
    );

    // Private repository
    expect(screen.getByTestId('lock-icon') || screen.querySelector('[data-testid="lock-icon"]')).toBeTruthy();

    // Public repository
    rerender(
      <RepositoryCard repository={{ ...mockRepository, visibility: 'public' }} />
    );
    expect(screen.getByTestId('globe-icon') || screen.querySelector('[data-testid="globe-icon"]')).toBeTruthy();
  });

  it('should format last sync time correctly', () => {
    render(<RepositoryCard repository={mockRepository} />);

    expect(screen.getByText(/Last synced.*ago/)).toBeInTheDocument();
  });

  it('should handle missing description gracefully', () => {
    const repoWithoutDescription = { ...mockRepository, description: undefined };
    
    render(<RepositoryCard repository={repoWithoutDescription} />);

    // Should not crash and should render other information
    expect(screen.getByText('test-repository')).toBeInTheDocument();
  });

  it('should handle missing language gracefully', () => {
    const repoWithoutLanguage = { ...mockRepository, language: undefined };
    
    render(<RepositoryCard repository={repoWithoutLanguage} />);

    // Should not crash and should render other information
    expect(screen.getByText('test-repository')).toBeInTheDocument();
    expect(screen.queryByText('TypeScript')).not.toBeInTheDocument();
  });

  it('should show building animation for building status', () => {
    render(
      <RepositoryCard repository={{ ...mockRepository, deploymentStatus: 'building' }} />
    );

    const buildingIcon = screen.getByText('Building').parentElement?.querySelector('.animate-spin');
    expect(buildingIcon).toBeInTheDocument();
  });
});