import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ProjectCard, type Project } from '../ProjectCard';

const mockProject: Project = {
  id: '1',
  name: 'Test Project',
  description: 'A test project for unit testing',
  ownerId: 'user-1',
  ownerName: 'John Doe',
  memberCount: 5,
  repositoryCount: 3,
  lastActivity: new Date('2024-01-15T10:00:00Z'),
  createdAt: new Date('2024-01-01T10:00:00Z'),
  status: 'active',
  visibility: 'private',
};

describe('ProjectCard', () => {
  const mockOnEdit = vi.fn();
  const mockOnDelete = vi.fn();
  const mockOnInviteMembers = vi.fn();
  const mockOnViewProject = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render project information correctly', () => {
    render(
      <ProjectCard
        project={mockProject}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onInviteMembers={mockOnInviteMembers}
        onViewProject={mockOnViewProject}
      />
    );

    expect(screen.getByText('Test Project')).toBeInTheDocument();
    expect(screen.getByText('A test project for unit testing')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('🔒 Private')).toBeInTheDocument();
    expect(screen.getByText('5 members')).toBeInTheDocument();
    expect(screen.getByText('3 repositories')).toBeInTheDocument();
    expect(screen.getByText('Owner: John Doe')).toBeInTheDocument();
  });

  it('should display correct status styling for different statuses', () => {
    const { rerender } = render(
      <ProjectCard project={mockProject} />
    );

    // Active status
    expect(screen.getByText('Active')).toHaveClass('bg-green-100', 'text-green-800');

    // Archived status
    rerender(
      <ProjectCard project={{ ...mockProject, status: 'archived' }} />
    );
    expect(screen.getByText('Archived')).toHaveClass('bg-gray-100', 'text-gray-800');

    // Draft status
    rerender(
      <ProjectCard project={{ ...mockProject, status: 'draft' }} />
    );
    expect(screen.getByText('Draft')).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });

  it('should display correct visibility indicator', () => {
    const { rerender } = render(
      <ProjectCard project={mockProject} />
    );

    // Private project
    expect(screen.getByText('🔒 Private')).toBeInTheDocument();

    // Public project
    rerender(
      <ProjectCard project={{ ...mockProject, visibility: 'public' }} />
    );
    expect(screen.getByText('🌐 Public')).toBeInTheDocument();
  });

  it('should show actions menu when showActions is true and user is owner', async () => {
    render(
      <ProjectCard
        project={mockProject}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onInviteMembers={mockOnInviteMembers}
        onViewProject={mockOnViewProject}
        showActions={true}
        isOwner={true}
      />
    );

    // Click the menu button
    const menuButton = screen.getByRole('button');
    fireEvent.click(menuButton);

    await waitFor(() => {
      expect(screen.getByText('View Project')).toBeInTheDocument();
      expect(screen.getByText('Edit Project')).toBeInTheDocument();
      expect(screen.getByText('Invite Members')).toBeInTheDocument();
      expect(screen.getByText('Delete Project')).toBeInTheDocument();
    });
  });

  it('should hide owner-specific actions when user is not owner', async () => {
    render(
      <ProjectCard
        project={mockProject}
        onEdit={mockOnEdit}
        onDelete={mockOnDelete}
        onInviteMembers={mockOnInviteMembers}
        onViewProject={mockOnViewProject}
        showActions={true}
        isOwner={false}
      />
    );

    // Click the menu button
    const menuButton = screen.getByRole('button');
    fireEvent.click(menuButton);

    await waitFor(() => {
      expect(screen.getByText('View Project')).toBeInTheDocument();
      expect(screen.queryByText('Edit Project')).not.toBeInTheDocument();
      expect(screen.queryByText('Invite Members')).not.toBeInTheDocument();
      expect(screen.queryByText('Delete Project')).not.toBeInTheDocument();
    });
  });

  it('should call onViewProject when View Project is clicked', async () => {
    render(
      <ProjectCard
        project={mockProject}
        onViewProject={mockOnViewProject}
        showActions={true}
        isOwner={true}
      />
    );

    // Click the menu button
    const menuButton = screen.getByRole('button');
    fireEvent.click(menuButton);

    await waitFor(() => {
      const viewButton = screen.getByText('View Project');
      fireEvent.click(viewButton);
    });

    expect(mockOnViewProject).toHaveBeenCalledWith(mockProject);
  });

  it('should call onEdit when Edit Project is clicked', async () => {
    render(
      <ProjectCard
        project={mockProject}
        onEdit={mockOnEdit}
        showActions={true}
        isOwner={true}
      />
    );

    // Click the menu button
    const menuButton = screen.getByRole('button');
    fireEvent.click(menuButton);

    await waitFor(() => {
      const editButton = screen.getByText('Edit Project');
      fireEvent.click(editButton);
    });

    expect(mockOnEdit).toHaveBeenCalledWith(mockProject);
  });

  it('should call onInviteMembers when Invite Members is clicked', async () => {
    render(
      <ProjectCard
        project={mockProject}
        onInviteMembers={mockOnInviteMembers}
        showActions={true}
        isOwner={true}
      />
    );

    // Click the menu button
    const menuButton = screen.getByRole('button');
    fireEvent.click(menuButton);

    await waitFor(() => {
      const inviteButton = screen.getByText('Invite Members');
      fireEvent.click(inviteButton);
    });

    expect(mockOnInviteMembers).toHaveBeenCalledWith(mockProject);
  });

  it('should call onDelete when Delete Project is clicked', async () => {
    render(
      <ProjectCard
        project={mockProject}
        onDelete={mockOnDelete}
        showActions={true}
        isOwner={true}
      />
    );

    // Click the menu button
    const menuButton = screen.getByRole('button');
    fireEvent.click(menuButton);

    await waitFor(() => {
      const deleteButton = screen.getByText('Delete Project');
      fireEvent.click(deleteButton);
    });

    expect(mockOnDelete).toHaveBeenCalledWith(mockProject);
  });

  it('should call onViewProject when Open Project button is clicked', () => {
    render(
      <ProjectCard
        project={mockProject}
        onViewProject={mockOnViewProject}
      />
    );

    const openButton = screen.getByText('Open Project');
    fireEvent.click(openButton);

    expect(mockOnViewProject).toHaveBeenCalledWith(mockProject);
  });

  it('should handle missing description gracefully', () => {
    const projectWithoutDescription = { ...mockProject, description: '' };
    
    render(
      <ProjectCard project={projectWithoutDescription} />
    );

    expect(screen.getByText('No description provided')).toBeInTheDocument();
  });

  it('should not show actions when showActions is false', () => {
    render(
      <ProjectCard
        project={mockProject}
        showActions={false}
      />
    );

    // Should not have the menu button
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('should close menu when clicking outside', async () => {
    render(
      <ProjectCard
        project={mockProject}
        showActions={true}
        isOwner={true}
      />
    );

    // Click the menu button to open
    const menuButton = screen.getByRole('button');
    fireEvent.click(menuButton);

    await waitFor(() => {
      expect(screen.getByText('View Project')).toBeInTheDocument();
    });

    // Click outside to close (simulate by clicking the menu button again)
    fireEvent.click(menuButton);

    await waitFor(() => {
      expect(screen.queryByText('View Project')).not.toBeInTheDocument();
    });
  });

  it('should format dates correctly', () => {
    render(<ProjectCard project={mockProject} />);

    // Should show relative time formatting
    expect(screen.getByText(/Created.*ago/)).toBeInTheDocument();
    expect(screen.getByText(/Last activity.*ago/)).toBeInTheDocument();
  });
});