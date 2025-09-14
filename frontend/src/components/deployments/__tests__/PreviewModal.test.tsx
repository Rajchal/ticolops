import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PreviewModal } from '../PreviewModal';
import type { Deployment } from '../DeploymentCard';

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
  logs: [],
  buildCommand: 'npm run build',
  environment: 'production',
};

describe('PreviewModal', () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock window.open
    Object.defineProperty(window, 'open', {
      writable: true,
      value: vi.fn(),
    });

    // Mock navigator.clipboard
    Object.defineProperty(navigator, 'clipboard', {
      writable: true,
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  it('should not render when isOpen is false', () => {
    render(
      <PreviewModal
        isOpen={false}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    expect(screen.queryByText('Preview')).not.toBeInTheDocument();
  });

  it('should render when isOpen is true', () => {
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    expect(screen.getByText('Preview')).toBeInTheDocument();
    expect(screen.getByText('test-repository • a1b2c3d • main')).toBeInTheDocument();
  });

  it('should not render when deployment is null', () => {
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={null}
      />
    );

    expect(screen.queryByText('Preview')).not.toBeInTheDocument();
  });

  it('should call onClose when close button is clicked', () => {
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('should display viewport size controls', () => {
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    expect(screen.getByText('Mobile')).toBeInTheDocument();
    expect(screen.getByText('Tablet')).toBeInTheDocument();
    expect(screen.getByText('Desktop')).toBeInTheDocument();
  });

  it('should switch viewport sizes', () => {
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    // Default should be desktop
    expect(screen.getByText('1200 × 800')).toBeInTheDocument();

    // Switch to mobile
    const mobileButton = screen.getByText('Mobile');
    fireEvent.click(mobileButton);

    expect(screen.getByText('375 × 667')).toBeInTheDocument();

    // Switch to tablet
    const tabletButton = screen.getByText('Tablet');
    fireEvent.click(tabletButton);

    expect(screen.getByText('768 × 1024')).toBeInTheDocument();
  });

  it('should display preview URL', () => {
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    expect(screen.getByText('https://test-repository.vercel.app')).toBeInTheDocument();
  });

  it('should copy URL to clipboard', async () => {
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    const copyButton = screen.getByText('Copy URL');
    fireEvent.click(copyButton);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('https://test-repository.vercel.app');

    await waitFor(() => {
      expect(screen.getByText('Copied!')).toBeInTheDocument();
    });
  });

  it('should open preview in new tab', () => {
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    const openButton = screen.getByText('Open in New Tab');
    fireEvent.click(openButton);

    expect(window.open).toHaveBeenCalledWith('https://test-repository.vercel.app', '_blank');
  });

  it('should render iframe with correct src', () => {
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    const iframe = screen.getByTitle('Preview of test-repository');
    expect(iframe).toHaveAttribute('src', 'https://test-repository.vercel.app');
  });

  it('should show loading state initially', () => {
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    expect(screen.getByText('Loading preview...')).toBeInTheDocument();
  });

  it('should handle iframe load event', () => {
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    const iframe = screen.getByTitle('Preview of test-repository');
    fireEvent.load(iframe);

    // Loading state should be removed
    expect(screen.queryByText('Loading preview...')).not.toBeInTheDocument();
  });

  it('should handle iframe error event', () => {
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    const iframe = screen.getByTitle('Preview of test-repository');
    fireEvent.error(iframe);

    expect(screen.getByText('Failed to Load Preview')).toBeInTheDocument();
    expect(screen.getByText('The preview could not be loaded. This might be due to:')).toBeInTheDocument();
  });

  it('should show refresh button and handle refresh', () => {
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    const refreshButton = screen.getByText('Refresh');
    expect(refreshButton).toBeInTheDocument();

    fireEvent.click(refreshButton);

    // Should show loading state after refresh
    expect(screen.getByText('Loading preview...')).toBeInTheDocument();
  });

  it('should display deployment information in status bar', () => {
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    expect(screen.getByText('Deployment: success')).toBeInTheDocument();
    expect(screen.getByText(/Deployed.*2024/)).toBeInTheDocument();
    expect(screen.getByText('Build time: 2m 0s')).toBeInTheDocument();
  });

  it('should handle share functionality', () => {
    // Mock navigator.share
    Object.defineProperty(navigator, 'share', {
      writable: true,
      value: vi.fn().mockResolvedValue(undefined),
    });

    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    const shareButton = screen.getByText('Share');
    fireEvent.click(shareButton);

    expect(navigator.share).toHaveBeenCalledWith({
      title: 'Preview: test-repository',
      url: 'https://test-repository.vercel.app',
    });
  });

  it('should fallback to copy when share is not available', async () => {
    // Don't mock navigator.share to simulate unavailability
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    const shareButton = screen.getByText('Share');
    fireEvent.click(shareButton);

    // Should fallback to clipboard copy
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('https://test-repository.vercel.app');
  });

  it('should handle deployment without preview URL', () => {
    const deploymentWithoutUrl = {
      ...mockDeployment,
      url: undefined,
      previewUrl: undefined,
    };

    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={deploymentWithoutUrl}
      />
    );

    // Should not render the modal
    expect(screen.queryByText('Preview')).not.toBeInTheDocument();
  });

  it('should use previewUrl when url is not available', () => {
    const deploymentWithPreviewUrl = {
      ...mockDeployment,
      url: undefined,
      previewUrl: 'https://preview.test-repository.vercel.app',
    };

    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={deploymentWithPreviewUrl}
      />
    );

    expect(screen.getByText('https://preview.test-repository.vercel.app')).toBeInTheDocument();
    
    const iframe = screen.getByTitle('Preview of test-repository');
    expect(iframe).toHaveAttribute('src', 'https://preview.test-repository.vercel.app');
  });

  it('should show error recovery options', () => {
    render(
      <PreviewModal
        isOpen={true}
        onClose={mockOnClose}
        deployment={mockDeployment}
      />
    );

    // Trigger error state
    const iframe = screen.getByTitle('Preview of test-repository');
    fireEvent.error(iframe);

    expect(screen.getByText('Try Again')).toBeInTheDocument();
    expect(screen.getByText('Open Directly')).toBeInTheDocument();

    // Test Try Again button
    const tryAgainButton = screen.getByText('Try Again');
    fireEvent.click(tryAgainButton);

    expect(screen.getByText('Loading preview...')).toBeInTheDocument();

    // Test Open Directly button
    fireEvent.error(iframe); // Trigger error again
    const openDirectlyButton = screen.getByText('Open Directly');
    fireEvent.click(openDirectlyButton);

    expect(window.open).toHaveBeenCalledWith('https://test-repository.vercel.app', '_blank');
  });
});