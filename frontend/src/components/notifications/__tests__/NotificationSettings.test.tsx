import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { NotificationSettings } from '../NotificationSettings';

const mockPreferences = {
  email: {
    enabled: true,
    activity: false,
    deployment: true,
    mentions: true,
    conflicts: true,
    system: false,
    digest: 'daily' as const,
  },
  inApp: {
    enabled: true,
    activity: true,
    deployment: true,
    mentions: true,
    conflicts: true,
    system: true,
    sound: true,
  },
  push: {
    enabled: false,
    activity: false,
    deployment: true,
    mentions: true,
    conflicts: true,
    system: false,
  },
  quietHours: {
    enabled: false,
    startTime: '22:00',
    endTime: '08:00',
    timezone: 'America/New_York',
  },
  keywords: ['urgent', 'bug'],
  projects: ['project-1'],
};

const mockProjects = [
  { id: 'project-1', name: 'Test Project 1' },
  { id: 'project-2', name: 'Test Project 2' },
  { id: 'project-3', name: 'Test Project 3' },
];

describe('NotificationSettings', () => {
  const mockOnClose = vi.fn();
  const mockOnSave = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockOnSave.mockResolvedValue(undefined);
  });

  it('does not render when isOpen is false', () => {
    render(
      <NotificationSettings
        isOpen={false}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    expect(screen.queryByText('Notification Settings')).not.toBeInTheDocument();
  });

  it('renders when isOpen is true', () => {
    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    expect(screen.getByText('Notification Settings')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('displays current preferences correctly', () => {
    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    // Check in-app notifications are enabled
    const inAppEnabled = screen.getByLabelText('Enable in-app notifications');
    expect(inAppEnabled).toBeChecked();

    // Check email notifications are enabled
    const emailEnabled = screen.getByLabelText('Enable email notifications');
    expect(emailEnabled).toBeChecked();

    // Check push notifications are disabled
    const pushEnabled = screen.getByLabelText('Enable push notifications');
    expect(pushEnabled).not.toBeChecked();

    // Check sound is enabled
    const soundEnabled = screen.getByLabelText('Play notification sounds');
    expect(soundEnabled).toBeChecked();
  });

  it('toggles in-app notification settings', () => {
    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    const inAppEnabled = screen.getByLabelText('Enable in-app notifications');
    fireEvent.click(inAppEnabled);

    expect(inAppEnabled).not.toBeChecked();
  });

  it('toggles email notification settings', () => {
    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    const emailEnabled = screen.getByLabelText('Enable email notifications');
    fireEvent.click(emailEnabled);

    expect(emailEnabled).not.toBeChecked();
  });

  it('changes email digest frequency', () => {
    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    const digestSelect = screen.getByDisplayValue('daily');
    fireEvent.change(digestSelect, { target: { value: 'weekly' } });

    expect(digestSelect).toHaveValue('weekly');
  });

  it('toggles quiet hours settings', () => {
    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    const quietHoursEnabled = screen.getByLabelText('Enable quiet hours');
    fireEvent.click(quietHoursEnabled);

    expect(quietHoursEnabled).toBeChecked();

    // Should show time inputs when enabled
    expect(screen.getByLabelText('Start time')).toBeInTheDocument();
    expect(screen.getByLabelText('End time')).toBeInTheDocument();
  });

  it('adds and removes keywords', async () => {
    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    // Check existing keywords are displayed
    expect(screen.getByText('urgent')).toBeInTheDocument();
    expect(screen.getByText('bug')).toBeInTheDocument();

    // Add a new keyword
    const keywordInput = screen.getByPlaceholderText('Add keyword...');
    fireEvent.change(keywordInput, { target: { value: 'security' } });
    
    const addButton = screen.getByText('Add');
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getByText('security')).toBeInTheDocument();
    });

    // Remove a keyword
    const urgentKeyword = screen.getByText('urgent').parentElement;
    const removeButton = urgentKeyword?.querySelector('button');
    if (removeButton) {
      fireEvent.click(removeButton);
    }

    await waitFor(() => {
      expect(screen.queryByText('urgent')).not.toBeInTheDocument();
    });
  });

  it('adds keyword on Enter key press', async () => {
    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    const keywordInput = screen.getByPlaceholderText('Add keyword...');
    fireEvent.change(keywordInput, { target: { value: 'critical' } });
    fireEvent.keyPress(keywordInput, { key: 'Enter', code: 'Enter' });

    await waitFor(() => {
      expect(screen.getByText('critical')).toBeInTheDocument();
    });
  });

  it('toggles project subscriptions', () => {
    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    // Project 1 should be checked (in preferences)
    const project1Checkbox = screen.getByLabelText('Test Project 1');
    expect(project1Checkbox).toBeChecked();

    // Project 2 should not be checked
    const project2Checkbox = screen.getByLabelText('Test Project 2');
    expect(project2Checkbox).not.toBeChecked();

    // Toggle project 2
    fireEvent.click(project2Checkbox);
    expect(project2Checkbox).toBeChecked();

    // Toggle project 1 off
    fireEvent.click(project1Checkbox);
    expect(project1Checkbox).not.toBeChecked();
  });

  it('calls onSave with updated preferences when save is clicked', async () => {
    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    // Make a change
    const pushEnabled = screen.getByLabelText('Enable push notifications');
    fireEvent.click(pushEnabled);

    // Save
    const saveButton = screen.getByText('Save Settings');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith(
        expect.objectContaining({
          push: expect.objectContaining({
            enabled: true,
          }),
        })
      );
    });
  });

  it('shows loading state when saving', async () => {
    // Make onSave return a pending promise
    let resolveSave: () => void;
    const savePromise = new Promise<void>((resolve) => {
      resolveSave = resolve;
    });
    mockOnSave.mockReturnValue(savePromise);

    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    const saveButton = screen.getByText('Save Settings');
    fireEvent.click(saveButton);

    // Should show loading state
    expect(screen.getByText('Saving...')).toBeInTheDocument();
    expect(saveButton).toBeDisabled();

    // Resolve the save
    resolveSave!();
    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it('resets to default preferences when reset is clicked', () => {
    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    // Make some changes first
    const pushEnabled = screen.getByLabelText('Enable push notifications');
    fireEvent.click(pushEnabled);
    expect(pushEnabled).toBeChecked();

    // Reset to defaults
    const resetButton = screen.getByText('Reset to Defaults');
    fireEvent.click(resetButton);

    // Should be back to default (disabled)
    expect(pushEnabled).not.toBeChecked();
  });

  it('calls onClose when cancel is clicked', () => {
    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('disables buttons when saving', async () => {
    // Make onSave return a pending promise
    let resolveSave: () => void;
    const savePromise = new Promise<void>((resolve) => {
      resolveSave = resolve;
    });
    mockOnSave.mockReturnValue(savePromise);

    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    const saveButton = screen.getByText('Save Settings');
    fireEvent.click(saveButton);

    // All buttons should be disabled during save
    expect(screen.getByText('Cancel')).toBeDisabled();
    expect(screen.getByText('Reset to Defaults')).toBeDisabled();

    // Resolve the save
    resolveSave!();
    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  it('prevents adding duplicate keywords', async () => {
    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    // Try to add existing keyword
    const keywordInput = screen.getByPlaceholderText('Add keyword...');
    fireEvent.change(keywordInput, { target: { value: 'urgent' } });
    
    const addButton = screen.getByText('Add');
    fireEvent.click(addButton);

    // Should not add duplicate - still only one 'urgent' keyword
    const urgentKeywords = screen.getAllByText('urgent');
    expect(urgentKeywords).toHaveLength(1);
  });

  it('prevents adding empty keywords', () => {
    render(
      <NotificationSettings
        isOpen={true}
        onClose={mockOnClose}
        preferences={mockPreferences}
        onSave={mockOnSave}
        availableProjects={mockProjects}
      />
    );

    const addButton = screen.getByText('Add');
    expect(addButton).toBeDisabled();

    // Try with whitespace only
    const keywordInput = screen.getByPlaceholderText('Add keyword...');
    fireEvent.change(keywordInput, { target: { value: '   ' } });
    
    expect(addButton).toBeDisabled();
  });
});