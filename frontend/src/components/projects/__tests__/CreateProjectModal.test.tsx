import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CreateProjectModal, type CreateProjectData } from '../CreateProjectModal';

describe('CreateProjectModal', () => {
  const mockOnClose = vi.fn();
  const mockOnSubmit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should not render when isOpen is false', () => {
    render(
      <CreateProjectModal
        isOpen={false}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    expect(screen.queryByText('Create New Project')).not.toBeInTheDocument();
  });

  it('should render when isOpen is true', () => {
    render(
      <CreateProjectModal
        isOpen={true}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    expect(screen.getByText('Create New Project')).toBeInTheDocument();
    expect(screen.getByLabelText('Project Name *')).toBeInTheDocument();
    expect(screen.getByLabelText('Description *')).toBeInTheDocument();
    expect(screen.getByText('Visibility')).toBeInTheDocument();
  });

  it('should call onClose when close button is clicked', () => {
    render(
      <CreateProjectModal
        isOpen={true}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('should call onClose when cancel button is clicked', () => {
    render(
      <CreateProjectModal
        isOpen={true}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('should show validation errors for empty required fields', async () => {
    const user = userEvent.setup();
    
    render(
      <CreateProjectModal
        isOpen={true}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    const submitButton = screen.getByRole('button', { name: /create project/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Project name is required')).toBeInTheDocument();
      expect(screen.getByText('Project description is required')).toBeInTheDocument();
    });

    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('should show validation error for short project name', async () => {
    const user = userEvent.setup();
    
    render(
      <CreateProjectModal
        isOpen={true}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    const nameInput = screen.getByLabelText('Project Name *');
    await user.type(nameInput, 'AB');

    const submitButton = screen.getByRole('button', { name: /create project/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Project name must be at least 3 characters')).toBeInTheDocument();
    });
  });

  it('should show validation error for short description', async () => {
    const user = userEvent.setup();
    
    render(
      <CreateProjectModal
        isOpen={true}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    const nameInput = screen.getByLabelText('Project Name *');
    const descriptionInput = screen.getByLabelText('Description *');
    
    await user.type(nameInput, 'Valid Project Name');
    await user.type(descriptionInput, 'Short');

    const submitButton = screen.getByRole('button', { name: /create project/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Description must be at least 10 characters')).toBeInTheDocument();
    });
  });

  it('should submit form with valid data', async () => {
    const user = userEvent.setup();
    mockOnSubmit.mockResolvedValue(undefined);
    
    render(
      <CreateProjectModal
        isOpen={true}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    const nameInput = screen.getByLabelText('Project Name *');
    const descriptionInput = screen.getByLabelText('Description *');
    
    await user.type(nameInput, 'Test Project');
    await user.type(descriptionInput, 'This is a test project description');

    const submitButton = screen.getByRole('button', { name: /create project/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Test Project',
        description: 'This is a test project description',
        visibility: 'private',
        initialMembers: [],
      });
    });
  });

  it('should handle visibility selection', async () => {
    const user = userEvent.setup();
    mockOnSubmit.mockResolvedValue(undefined);
    
    render(
      <CreateProjectModal
        isOpen={true}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    // Select public visibility
    const publicRadio = screen.getByLabelText(/public/i);
    await user.click(publicRadio);

    const nameInput = screen.getByLabelText('Project Name *');
    const descriptionInput = screen.getByLabelText('Description *');
    
    await user.type(nameInput, 'Test Project');
    await user.type(descriptionInput, 'This is a test project description');

    const submitButton = screen.getByRole('button', { name: /create project/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Test Project',
        description: 'This is a test project description',
        visibility: 'public',
        initialMembers: [],
      });
    });
  });

  it('should add and remove team members', async () => {
    const user = userEvent.setup();
    
    render(
      <CreateProjectModal
        isOpen={true}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    const memberEmailInput = screen.getByPlaceholderText('Enter email address');
    const addButton = screen.getByRole('button', { name: /add/i });

    // Add a member
    await user.type(memberEmailInput, 'test@example.com');
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByText('test@example.com')).toBeInTheDocument();
      expect(screen.getByText('Members to invite (1):')).toBeInTheDocument();
    });

    // Remove the member
    const removeButton = screen.getByRole('button', { name: /remove/i });
    await user.click(removeButton);

    await waitFor(() => {
      expect(screen.queryByText('test@example.com')).not.toBeInTheDocument();
      expect(screen.queryByText('Members to invite (1):')).not.toBeInTheDocument();
    });
  });

  it('should add member on Enter key press', async () => {
    const user = userEvent.setup();
    
    render(
      <CreateProjectModal
        isOpen={true}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    const memberEmailInput = screen.getByPlaceholderText('Enter email address');

    await user.type(memberEmailInput, 'test@example.com');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText('test@example.com')).toBeInTheDocument();
    });
  });

  it('should not add duplicate members', async () => {
    const user = userEvent.setup();
    
    render(
      <CreateProjectModal
        isOpen={true}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    const memberEmailInput = screen.getByPlaceholderText('Enter email address');
    const addButton = screen.getByRole('button', { name: /add/i });

    // Add a member twice
    await user.type(memberEmailInput, 'test@example.com');
    await user.click(addButton);
    
    await user.type(memberEmailInput, 'test@example.com');
    await user.click(addButton);

    // Should only show one instance
    const memberElements = screen.getAllByText('test@example.com');
    expect(memberElements).toHaveLength(1);
  });

  it('should include initial members in submission', async () => {
    const user = userEvent.setup();
    mockOnSubmit.mockResolvedValue(undefined);
    
    render(
      <CreateProjectModal
        isOpen={true}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    // Add members
    const memberEmailInput = screen.getByPlaceholderText('Enter email address');
    const addButton = screen.getByRole('button', { name: /add/i });

    await user.type(memberEmailInput, 'member1@example.com');
    await user.click(addButton);
    
    await user.type(memberEmailInput, 'member2@example.com');
    await user.click(addButton);

    // Fill required fields
    const nameInput = screen.getByLabelText('Project Name *');
    const descriptionInput = screen.getByLabelText('Description *');
    
    await user.type(nameInput, 'Test Project');
    await user.type(descriptionInput, 'This is a test project description');

    const submitButton = screen.getByRole('button', { name: /create project/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Test Project',
        description: 'This is a test project description',
        visibility: 'private',
        initialMembers: ['member1@example.com', 'member2@example.com'],
      });
    });
  });

  it('should show loading state during submission', async () => {
    const user = userEvent.setup();
    
    render(
      <CreateProjectModal
        isOpen={true}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
        isLoading={true}
      />
    );

    expect(screen.getByText('Creating...')).toBeInTheDocument();
    
    const submitButton = screen.getByRole('button', { name: /creating/i });
    expect(submitButton).toBeDisabled();
    
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    expect(cancelButton).toBeDisabled();
  });

  it('should reset form after successful submission', async () => {
    const user = userEvent.setup();
    mockOnSubmit.mockResolvedValue(undefined);
    
    render(
      <CreateProjectModal
        isOpen={true}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    // Fill form
    const nameInput = screen.getByLabelText('Project Name *');
    const descriptionInput = screen.getByLabelText('Description *');
    
    await user.type(nameInput, 'Test Project');
    await user.type(descriptionInput, 'This is a test project description');

    const submitButton = screen.getByRole('button', { name: /create project/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalled();
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it('should handle submission errors', async () => {
    const user = userEvent.setup();
    const error = new Error('Failed to create project');
    mockOnSubmit.mockRejectedValue(error);
    
    render(
      <CreateProjectModal
        isOpen={true}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    // Fill form
    const nameInput = screen.getByLabelText('Project Name *');
    const descriptionInput = screen.getByLabelText('Description *');
    
    await user.type(nameInput, 'Test Project');
    await user.type(descriptionInput, 'This is a test project description');

    const submitButton = screen.getByRole('button', { name: /create project/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Failed to create project. Please try again.')).toBeInTheDocument();
    });

    expect(mockOnClose).not.toHaveBeenCalled();
  });
});