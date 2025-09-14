import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConnectRepositoryModal, type ConnectRepositoryData } from '../ConnectRepositoryModal';

describe('ConnectRepositoryModal', () => {
  const mockOnClose = vi.fn();
  const mockOnConnect = vi.fn();
  const projectId = 'test-project-id';
  const projectName = 'Test Project';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should not render when isOpen is false', () => {
    render(
      <ConnectRepositoryModal
        isOpen={false}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
      />
    );

    expect(screen.queryByText('Connect Repository')).not.toBeInTheDocument();
  });

  it('should render when isOpen is true', () => {
    render(
      <ConnectRepositoryModal
        isOpen={true}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
      />
    );

    expect(screen.getByText('Connect Repository')).toBeInTheDocument();
    expect(screen.getByText(`Connect a Git repository to "${projectName}"`)).toBeInTheDocument();
  });

  it('should show step indicator', () => {
    render(
      <ConnectRepositoryModal
        isOpen={true}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
      />
    );

    expect(screen.getByText('Repository')).toBeInTheDocument();
    expect(screen.getByText('Details')).toBeInTheDocument();
    expect(screen.getByText('Configuration')).toBeInTheDocument();
  });

  it('should start on provider step', () => {
    render(
      <ConnectRepositoryModal
        isOpen={true}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
      />
    );

    expect(screen.getByLabelText('Repository URL')).toBeInTheDocument();
    expect(screen.getByText('Supported Providers')).toBeInTheDocument();
    expect(screen.getByText('GitHub')).toBeInTheDocument();
    expect(screen.getByText('GitLab')).toBeInTheDocument();
    expect(screen.getByText('Bitbucket')).toBeInTheDocument();
  });

  it('should validate repository URL', async () => {
    const user = userEvent.setup();
    
    render(
      <ConnectRepositoryModal
        isOpen={true}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
      />
    );

    const nextButton = screen.getByText('Next');
    await user.click(nextButton);

    await waitFor(() => {
      expect(screen.getByText('Repository URL is required')).toBeInTheDocument();
    });
  });

  it('should validate URL format', async () => {
    const user = userEvent.setup();
    
    render(
      <ConnectRepositoryModal
        isOpen={true}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
      />
    );

    const urlInput = screen.getByLabelText('Repository URL');
    await user.type(urlInput, 'invalid-url');

    const nextButton = screen.getByText('Next');
    await user.click(nextButton);

    await waitFor(() => {
      expect(screen.getByText('Please enter a valid repository URL')).toBeInTheDocument();
    });
  });

  it('should auto-detect provider from URL', async () => {
    const user = userEvent.setup();
    
    render(
      <ConnectRepositoryModal
        isOpen={true}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
      />
    );

    const urlInput = screen.getByLabelText('Repository URL');
    await user.type(urlInput, 'https://github.com/user/repo');

    // GitHub should be automatically selected
    const githubProvider = screen.getByText('GitHub').closest('div');
    expect(githubProvider).toHaveClass('border-blue-500');
  });

  it('should proceed to details step with valid URL', async () => {
    const user = userEvent.setup();
    
    render(
      <ConnectRepositoryModal
        isOpen={true}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
      />
    );

    const urlInput = screen.getByLabelText('Repository URL');
    await user.type(urlInput, 'https://github.com/user/repo');

    const nextButton = screen.getByText('Next');
    await user.click(nextButton);

    await waitFor(() => {
      expect(screen.getByLabelText('Branch')).toBeInTheDocument();
      expect(screen.getByLabelText('Access Token (Optional)')).toBeInTheDocument();
    });
  });

  it('should validate branch name in details step', async () => {
    const user = userEvent.setup();
    
    render(
      <ConnectRepositoryModal
        isOpen={true}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
      />
    );

    // Go to details step
    const urlInput = screen.getByLabelText('Repository URL');
    await user.type(urlInput, 'https://github.com/user/repo');
    
    let nextButton = screen.getByText('Next');
    await user.click(nextButton);

    await waitFor(() => {
      expect(screen.getByLabelText('Branch')).toBeInTheDocument();
    });

    // Clear branch field and try to proceed
    const branchInput = screen.getByLabelText('Branch');
    await user.clear(branchInput);

    nextButton = screen.getByText('Next');
    await user.click(nextButton);

    await waitFor(() => {
      expect(screen.getByText('Branch name is required')).toBeInTheDocument();
    });
  });

  it('should proceed to configuration step', async () => {
    const user = userEvent.setup();
    
    render(
      <ConnectRepositoryModal
        isOpen={true}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
      />
    );

    // Step 1: Provider
    const urlInput = screen.getByLabelText('Repository URL');
    await user.type(urlInput, 'https://github.com/user/repo');
    
    let nextButton = screen.getByText('Next');
    await user.click(nextButton);

    // Step 2: Details
    await waitFor(() => {
      expect(screen.getByLabelText('Branch')).toBeInTheDocument();
    });

    nextButton = screen.getByText('Next');
    await user.click(nextButton);

    // Step 3: Configuration
    await waitFor(() => {
      expect(screen.getByText('Enable automatic deployments')).toBeInTheDocument();
      expect(screen.getByLabelText('Build Command (Optional)')).toBeInTheDocument();
      expect(screen.getByLabelText('Output Directory (Optional)')).toBeInTheDocument();
    });
  });

  it('should handle auto-deploy configuration', async () => {
    const user = userEvent.setup();
    
    render(
      <ConnectRepositoryModal
        isOpen={true}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
      />
    );

    // Navigate to configuration step
    const urlInput = screen.getByLabelText('Repository URL');
    await user.type(urlInput, 'https://github.com/user/repo');
    
    let nextButton = screen.getByText('Next');
    await user.click(nextButton);

    await waitFor(() => {
      nextButton = screen.getByText('Next');
    });
    await user.click(nextButton);

    await waitFor(() => {
      expect(screen.getByText('Enable automatic deployments')).toBeInTheDocument();
    });

    // Auto-deploy should be enabled by default
    const autoDeployCheckbox = screen.getByRole('checkbox');
    expect(autoDeployCheckbox).toBeChecked();

    // Build command and output directory should be visible
    expect(screen.getByLabelText('Build Command (Optional)')).toBeInTheDocument();
    expect(screen.getByLabelText('Output Directory (Optional)')).toBeInTheDocument();

    // Disable auto-deploy
    await user.click(autoDeployCheckbox);

    // Build command and output directory should be hidden
    expect(screen.queryByLabelText('Build Command (Optional)')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Output Directory (Optional)')).not.toBeInTheDocument();
  });

  it('should handle environment variables', async () => {
    const user = userEvent.setup();
    
    render(
      <ConnectRepositoryModal
        isOpen={true}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
      />
    );

    // Navigate to configuration step
    const urlInput = screen.getByLabelText('Repository URL');
    await user.type(urlInput, 'https://github.com/user/repo');
    
    let nextButton = screen.getByText('Next');
    await user.click(nextButton);

    await waitFor(() => {
      nextButton = screen.getByText('Next');
    });
    await user.click(nextButton);

    await waitFor(() => {
      expect(screen.getByText('Environment Variables')).toBeInTheDocument();
    });

    // Add environment variable
    const keyInput = screen.getByPlaceholderText('Variable name');
    const valueInput = screen.getByPlaceholderText('Variable value');
    const addButton = screen.getByText('Add');

    await user.type(keyInput, 'NODE_ENV');
    await user.type(valueInput, 'production');
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByText('NODE_ENV=production')).toBeInTheDocument();
    });

    // Remove environment variable
    const removeButton = screen.getByRole('button', { name: /remove/i });
    await user.click(removeButton);

    await waitFor(() => {
      expect(screen.queryByText('NODE_ENV=production')).not.toBeInTheDocument();
    });
  });

  it('should submit form with correct data', async () => {
    const user = userEvent.setup();
    mockOnConnect.mockResolvedValue(undefined);
    
    render(
      <ConnectRepositoryModal
        isOpen={true}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
      />
    );

    // Step 1: Provider
    const urlInput = screen.getByLabelText('Repository URL');
    await user.type(urlInput, 'https://github.com/user/test-repo');
    
    let nextButton = screen.getByText('Next');
    await user.click(nextButton);

    // Step 2: Details
    await waitFor(() => {
      expect(screen.getByLabelText('Branch')).toBeInTheDocument();
    });

    const branchInput = screen.getByLabelText('Branch');
    await user.clear(branchInput);
    await user.type(branchInput, 'develop');

    const tokenInput = screen.getByLabelText('Access Token (Optional)');
    await user.type(tokenInput, 'test-token');

    nextButton = screen.getByText('Next');
    await user.click(nextButton);

    // Step 3: Configuration
    await waitFor(() => {
      expect(screen.getByText('Enable automatic deployments')).toBeInTheDocument();
    });

    const buildCommandInput = screen.getByLabelText('Build Command (Optional)');
    await user.type(buildCommandInput, 'npm run build');

    const outputDirInput = screen.getByLabelText('Output Directory (Optional)');
    await user.type(outputDirInput, 'build');

    // Add environment variable
    const keyInput = screen.getByPlaceholderText('Variable name');
    const valueInput = screen.getByPlaceholderText('Variable value');
    const addButton = screen.getByText('Add');

    await user.type(keyInput, 'API_URL');
    await user.type(valueInput, 'https://api.example.com');
    await user.click(addButton);

    // Submit
    const connectButton = screen.getByText('Connect Repository');
    await user.click(connectButton);

    await waitFor(() => {
      expect(mockOnConnect).toHaveBeenCalledWith({
        url: 'https://github.com/user/test-repo',
        provider: 'github',
        branch: 'develop',
        accessToken: 'test-token',
        autoDeployEnabled: true,
        buildCommand: 'npm run build',
        outputDirectory: 'build',
        environmentVariables: {
          API_URL: 'https://api.example.com',
        },
      });
    });
  });

  it('should handle navigation between steps', async () => {
    const user = userEvent.setup();
    
    render(
      <ConnectRepositoryModal
        isOpen={true}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
      />
    );

    // Go to step 2
    const urlInput = screen.getByLabelText('Repository URL');
    await user.type(urlInput, 'https://github.com/user/repo');
    
    let nextButton = screen.getByText('Next');
    await user.click(nextButton);

    await waitFor(() => {
      expect(screen.getByLabelText('Branch')).toBeInTheDocument();
    });

    // Go to step 3
    nextButton = screen.getByText('Next');
    await user.click(nextButton);

    await waitFor(() => {
      expect(screen.getByText('Enable automatic deployments')).toBeInTheDocument();
    });

    // Go back to step 2
    const previousButton = screen.getByText('Previous');
    await user.click(previousButton);

    await waitFor(() => {
      expect(screen.getByLabelText('Branch')).toBeInTheDocument();
    });

    // Go back to step 1
    await user.click(previousButton);

    await waitFor(() => {
      expect(screen.getByLabelText('Repository URL')).toBeInTheDocument();
    });
  });

  it('should show loading state during submission', async () => {
    render(
      <ConnectRepositoryModal
        isOpen={true}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
        isLoading={true}
      />
    );

    // All buttons should be disabled during loading
    const buttons = screen.getAllByRole('button');
    buttons.forEach(button => {
      expect(button).toBeDisabled();
    });
  });

  it('should handle submission errors', async () => {
    const user = userEvent.setup();
    const error = new Error('Connection failed');
    mockOnConnect.mockRejectedValue(error);
    
    render(
      <ConnectRepositoryModal
        isOpen={true}
        onClose={mockOnClose}
        onConnect={mockOnConnect}
        projectId={projectId}
        projectName={projectName}
      />
    );

    // Navigate to final step and submit
    const urlInput = screen.getByLabelText('Repository URL');
    await user.type(urlInput, 'https://github.com/user/repo');
    
    let nextButton = screen.getByText('Next');
    await user.click(nextButton);

    await waitFor(() => {
      nextButton = screen.getByText('Next');
    });
    await user.click(nextButton);

    await waitFor(() => {
      const connectButton = screen.getByText('Connect Repository');
      await user.click(connectButton);
    });

    await waitFor(() => {
      expect(screen.getByText('Failed to connect repository. Please check your credentials and try again.')).toBeInTheDocument();
    });

    expect(mockOnClose).not.toHaveBeenCalled();
  });
});