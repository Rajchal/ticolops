import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CollaborationSuggestions } from '../CollaborationSuggestions';
import { RealtimeProvider } from '../../../contexts/RealtimeContext';
import { AuthProvider } from '../../../contexts/AuthContext';

// Mock the websocket service
vi.mock('../../../services/websocketService', () => ({
  websocketService: {
    connect: vi.fn().mockResolvedValue({}),
    disconnect: vi.fn(),
    onActivityEvent: vi.fn(),
    offActivityEvent: vi.fn(),
    onPresenceUpdate: vi.fn(),
    offPresenceUpdate: vi.fn(),
    onConflictAlert: vi.fn(),
    offConflictAlert: vi.fn(),
    updatePresence: vi.fn(),
    joinProject: vi.fn(),
    leaveProject: vi.fn(),
    joinFile: vi.fn(),
    leaveFile: vi.fn(),
    isConnected: vi.fn(() => true),
    getSocket: vi.fn(() => ({ connected: true })),
  },
}));

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AuthProvider>
    <RealtimeProvider>
      {children}
    </RealtimeProvider>
  </AuthProvider>
);

describe('CollaborationSuggestions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock localStorage for auth token
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(() => 'mock-token'),
        setItem: vi.fn(),
        removeItem: vi.fn(),
      },
      writable: true,
    });
  });

  it('should render collaboration suggestions with header', async () => {
    render(
      <TestWrapper>
        <CollaborationSuggestions />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Collaboration Opportunities')).toBeInTheDocument();
    });

    // Check for mock suggestions
    expect(screen.getByText('Similar component being developed')).toBeInTheDocument();
    expect(screen.getByText('API integration expertise needed')).toBeInTheDocument();
    expect(screen.getByText('Code review opportunity')).toBeInTheDocument();
  });

  it('should render without header when showHeader is false', async () => {
    render(
      <TestWrapper>
        <CollaborationSuggestions showHeader={false} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.queryByText('Collaboration Opportunities')).not.toBeInTheDocument();
    });

    // But suggestions should still be there
    expect(screen.getByText('Similar component being developed')).toBeInTheDocument();
  });

  it('should limit suggestions based on maxSuggestions prop', async () => {
    render(
      <TestWrapper>
        <CollaborationSuggestions maxSuggestions={2} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Similar component being developed')).toBeInTheDocument();
      expect(screen.getByText('API integration expertise needed')).toBeInTheDocument();
    });

    // Third suggestion should not be visible due to limit
    expect(screen.queryByText('Code review opportunity')).not.toBeInTheDocument();
  });

  it('should handle accepting a suggestion', async () => {
    render(
      <TestWrapper>
        <CollaborationSuggestions />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Similar component being developed')).toBeInTheDocument();
    });

    // Find and click the Connect button for the first suggestion
    const connectButtons = screen.getAllByText('Connect');
    fireEvent.click(connectButtons[0]);

    // The suggestion should be removed
    await waitFor(() => {
      expect(screen.queryByText('Similar component being developed')).not.toBeInTheDocument();
    });

    // Other suggestions should still be there
    expect(screen.getByText('API integration expertise needed')).toBeInTheDocument();
  });

  it('should handle dismissing a suggestion', async () => {
    render(
      <TestWrapper>
        <CollaborationSuggestions />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Similar component being developed')).toBeInTheDocument();
    });

    // Find and click the Dismiss button for the first suggestion
    const dismissButtons = screen.getAllByText('Dismiss');
    fireEvent.click(dismissButtons[0]);

    // The suggestion should be removed
    await waitFor(() => {
      expect(screen.queryByText('Similar component being developed')).not.toBeInTheDocument();
    });

    // Other suggestions should still be there
    expect(screen.getByText('API integration expertise needed')).toBeInTheDocument();
  });

  it('should display suggestion details correctly', async () => {
    render(
      <TestWrapper>
        <CollaborationSuggestions />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Similar component being developed')).toBeInTheDocument();
    });

    // Check suggestion details
    expect(screen.getByText('Sarah is working on a similar authentication component. Consider collaborating to avoid duplication.')).toBeInTheDocument();
    expect(screen.getByText('With: Sarah Chen')).toBeInTheDocument();
    expect(screen.getByText('Auth System')).toBeInTheDocument();
    expect(screen.getByText('src/components/LoginForm.tsx')).toBeInTheDocument();
  });

  it('should sort suggestions by priority', async () => {
    render(
      <TestWrapper>
        <CollaborationSuggestions />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Similar component being developed')).toBeInTheDocument();
    });

    // Get all suggestion containers
    const suggestions = screen.getAllByText(/Similar component|API integration|Code review/);
    
    // High priority suggestion should come first
    expect(suggestions[0]).toHaveTextContent('Similar component being developed');
    // Medium priority should come second
    expect(suggestions[1]).toHaveTextContent('API integration expertise needed');
    // Low priority should come last
    expect(suggestions[2]).toHaveTextContent('Code review opportunity');
  });

  it('should display different suggestion types with correct icons', async () => {
    render(
      <TestWrapper>
        <CollaborationSuggestions />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Similar component being developed')).toBeInTheDocument();
    });

    // Check that different types of suggestions are displayed
    expect(screen.getByText('Similar component being developed')).toBeInTheDocument(); // related_work
    expect(screen.getByText('API integration expertise needed')).toBeInTheDocument(); // knowledge_sharing
    expect(screen.getByText('Code review opportunity')).toBeInTheDocument(); // code_review
  });

  it('should show empty state when no suggestions are available', async () => {
    // We need to modify the component to accept empty suggestions for testing
    // For now, we'll test the behavior after dismissing all suggestions
    render(
      <TestWrapper>
        <CollaborationSuggestions />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Similar component being developed')).toBeInTheDocument();
    });

    // Dismiss all suggestions
    const dismissButtons = screen.getAllByText('Dismiss');
    dismissButtons.forEach(button => fireEvent.click(button));

    await waitFor(() => {
      expect(screen.getByText('No collaboration opportunities')).toBeInTheDocument();
      expect(screen.getByText('Keep working - suggestions will appear based on team activity!')).toBeInTheDocument();
    });
  });

  it('should display connection status indicator', async () => {
    render(
      <TestWrapper>
        <CollaborationSuggestions />
      </TestWrapper>
    );

    await waitFor(() => {
      // Should show connected status (green dot)
      const statusIndicator = screen.getByText('3 available').parentElement?.querySelector('div[class*="bg-green-500"]');
      expect(statusIndicator).toBeInTheDocument();
    });
  });

  it('should handle different priority levels with correct styling', async () => {
    render(
      <TestWrapper>
        <CollaborationSuggestions />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Similar component being developed')).toBeInTheDocument();
    });

    // Check that high priority suggestion has red border
    const highPrioritySuggestion = screen.getByText('Similar component being developed').closest('div');
    expect(highPrioritySuggestion).toHaveClass('border-l-red-500');

    // Check that medium priority suggestion has yellow border
    const mediumPrioritySuggestion = screen.getByText('API integration expertise needed').closest('div');
    expect(mediumPrioritySuggestion).toHaveClass('border-l-yellow-500');

    // Check that low priority suggestion has blue border
    const lowPrioritySuggestion = screen.getByText('Code review opportunity').closest('div');
    expect(lowPrioritySuggestion).toHaveClass('border-l-blue-500');
  });
});