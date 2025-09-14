import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Users, FileText, GitBranch, Lightbulb, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';
import { useRealtime } from '../../contexts/RealtimeContext';

interface CollaborationOpportunity {
  id: string;
  type: 'related_work' | 'knowledge_sharing' | 'code_review' | 'pair_programming';
  title: string;
  description: string;
  users: string[];
  projectId: string;
  projectName: string;
  filePath?: string;
  priority: 'low' | 'medium' | 'high';
  timestamp: Date;
}

const getSuggestionIcon = (type: CollaborationOpportunity['type']) => {
  switch (type) {
    case 'related_work':
      return <GitBranch className="h-4 w-4 text-blue-500" />;
    case 'knowledge_sharing':
      return <Lightbulb className="h-4 w-4 text-yellow-500" />;
    case 'code_review':
      return <FileText className="h-4 w-4 text-green-500" />;
    case 'pair_programming':
      return <Users className="h-4 w-4 text-purple-500" />;
    default:
      return <Users className="h-4 w-4 text-gray-500" />;
  }
};

const getPriorityColor = (priority: CollaborationOpportunity['priority']) => {
  switch (priority) {
    case 'high':
      return 'border-l-red-500 bg-red-50';
    case 'medium':
      return 'border-l-yellow-500 bg-yellow-50';
    case 'low':
      return 'border-l-blue-500 bg-blue-50';
    default:
      return 'border-l-gray-500 bg-gray-50';
  }
};

interface SuggestionItemProps {
  suggestion: CollaborationOpportunity;
  onAccept: (suggestionId: string) => void;
  onDismiss: (suggestionId: string) => void;
}

const SuggestionItem: React.FC<SuggestionItemProps> = ({ suggestion, onAccept, onDismiss }) => {
  return (
    <div className={`border-l-4 rounded-r-md p-4 ${getPriorityColor(suggestion.priority)}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1">
          <div className="flex-shrink-0 mt-1">
            {getSuggestionIcon(suggestion.type)}
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold text-gray-900">
              {suggestion.title}
            </h4>
            <p className="text-sm text-gray-700 mt-1">
              {suggestion.description}
            </p>
            <div className="flex items-center space-x-4 mt-2 text-xs text-gray-600">
              <span className="flex items-center space-x-1">
                <FileText className="h-3 w-3" />
                <span>{suggestion.projectName}</span>
              </span>
              {suggestion.filePath && (
                <span className="font-mono">{suggestion.filePath}</span>
              )}
              <span>
                {formatDistanceToNow(new Date(suggestion.timestamp), { addSuffix: true })}
              </span>
            </div>
            {suggestion.users.length > 0 && (
              <div className="flex items-center space-x-1 mt-2">
                <Users className="h-3 w-3 text-gray-500" />
                <span className="text-xs text-gray-600">
                  With: {suggestion.users.join(', ')}
                </span>
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center space-x-2 ml-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onAccept(suggestion.id)}
            className="text-xs"
          >
            <ArrowRight className="h-3 w-3 mr-1" />
            Connect
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onDismiss(suggestion.id)}
            className="text-xs"
          >
            Dismiss
          </Button>
        </div>
      </div>
    </div>
  );
};

interface CollaborationSuggestionsProps {
  showHeader?: boolean;
  maxSuggestions?: number;
}

export const CollaborationSuggestions: React.FC<CollaborationSuggestionsProps> = ({ 
  showHeader = true, 
  maxSuggestions = 5 
}) => {
  const { activities, userPresence, isConnected } = useRealtime();
  
  // Mock collaboration suggestions based on real-time data
  // In a real implementation, this would come from the backend
  const [suggestions, setSuggestions] = React.useState<CollaborationOpportunity[]>([
    {
      id: '1',
      type: 'related_work',
      title: 'Similar component being developed',
      description: 'Sarah is working on a similar authentication component. Consider collaborating to avoid duplication.',
      users: ['Sarah Chen'],
      projectId: 'proj-1',
      projectName: 'Auth System',
      filePath: 'src/components/LoginForm.tsx',
      priority: 'high',
      timestamp: new Date(Date.now() - 5 * 60 * 1000), // 5 minutes ago
    },
    {
      id: '2',
      type: 'knowledge_sharing',
      title: 'API integration expertise needed',
      description: 'Mike has experience with the payment API you\'re trying to integrate.',
      users: ['Mike Johnson'],
      projectId: 'proj-2',
      projectName: 'E-commerce Platform',
      priority: 'medium',
      timestamp: new Date(Date.now() - 15 * 60 * 1000), // 15 minutes ago
    },
    {
      id: '3',
      type: 'code_review',
      title: 'Code review opportunity',
      description: 'Your recent changes to the user service could benefit from Alex\'s database expertise.',
      users: ['Alex Rodriguez'],
      projectId: 'proj-1',
      projectName: 'User Management',
      filePath: 'src/services/userService.ts',
      priority: 'low',
      timestamp: new Date(Date.now() - 30 * 60 * 1000), // 30 minutes ago
    },
  ]);

  const handleAcceptSuggestion = (suggestionId: string) => {
    // In a real implementation, this would initiate collaboration
    console.log('Accepting collaboration suggestion:', suggestionId);
    setSuggestions(prev => prev.filter(s => s.id !== suggestionId));
  };

  const handleDismissSuggestion = (suggestionId: string) => {
    setSuggestions(prev => prev.filter(s => s.id !== suggestionId));
  };

  // Sort suggestions by priority and timestamp
  const sortedSuggestions = [...suggestions]
    .sort((a, b) => {
      const priorityOrder = { high: 0, medium: 1, low: 2 };
      const aPriority = priorityOrder[a.priority];
      const bPriority = priorityOrder[b.priority];
      
      if (aPriority !== bPriority) {
        return aPriority - bPriority;
      }
      
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    })
    .slice(0, maxSuggestions);

  if (showHeader) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Collaboration Opportunities</span>
            <div className="flex items-center space-x-2">
              <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-sm font-normal text-muted-foreground">
                {sortedSuggestions.length} available
              </span>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {sortedSuggestions.length > 0 ? (
              sortedSuggestions.map((suggestion) => (
                <SuggestionItem 
                  key={suggestion.id} 
                  suggestion={suggestion}
                  onAccept={handleAcceptSuggestion}
                  onDismiss={handleDismissSuggestion}
                />
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Lightbulb className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No collaboration opportunities</p>
                <p className="text-xs mt-1">Keep working - suggestions will appear based on team activity!</p>
                {!isConnected && (
                  <p className="text-xs mt-1 text-red-500">
                    Disconnected - collaboration suggestions unavailable
                  </p>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {sortedSuggestions.length > 0 ? (
        sortedSuggestions.map((suggestion) => (
          <SuggestionItem 
            key={suggestion.id} 
            suggestion={suggestion}
            onAccept={handleAcceptSuggestion}
            onDismiss={handleDismissSuggestion}
          />
        ))
      ) : (
        <div className="text-center py-8 text-muted-foreground">
          <Lightbulb className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>No collaboration opportunities</p>
          <p className="text-xs mt-1">Keep working - suggestions will appear based on team activity!</p>
          {!isConnected && (
            <p className="text-xs mt-1 text-red-500">
              Disconnected - collaboration suggestions unavailable
            </p>
          )}
        </div>
      )}
    </div>
  );
};