import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { AlertTriangle, X, GitMerge, Lock, Edit, Lightbulb } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';
import { useRealtime } from '../../contexts/RealtimeContext';
import type { ConflictAlert } from '../../services/websocketService';

const getConflictIcon = (type: ConflictAlert['type']) => {
  switch (type) {
    case 'merge_conflict':
      return <GitMerge className="h-4 w-4" />;
    case 'file_lock':
      return <Lock className="h-4 w-4" />;
    case 'simultaneous_edit':
      return <Edit className="h-4 w-4" />;
    default:
      return <AlertTriangle className="h-4 w-4" />;
  }
};

const getSeverityColor = (severity: ConflictAlert['severity']) => {
  switch (severity) {
    case 'high':
      return 'border-red-500 bg-red-50 text-red-900';
    case 'medium':
      return 'border-yellow-500 bg-yellow-50 text-yellow-900';
    case 'low':
      return 'border-blue-500 bg-blue-50 text-blue-900';
    default:
      return 'border-gray-500 bg-gray-50 text-gray-900';
  }
};

const getConflictTitle = (type: ConflictAlert['type']) => {
  switch (type) {
    case 'merge_conflict':
      return 'Merge Conflict Detected';
    case 'file_lock':
      return 'File Lock Conflict';
    case 'simultaneous_edit':
      return 'Simultaneous Edit Detected';
    default:
      return 'Conflict Detected';
  }
};

interface ConflictItemProps {
  conflict: ConflictAlert;
  onDismiss: (conflictId: string) => void;
}

const ConflictItem: React.FC<ConflictItemProps> = ({ conflict, onDismiss }) => {
  return (
    <div className={`border rounded-lg p-4 ${getSeverityColor(conflict.severity)}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0 mt-1">
            {getConflictIcon(conflict.type)}
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold">
              {getConflictTitle(conflict.type)}
            </h4>
            <p className="text-sm mt-1">
              <span className="font-medium">{conflict.projectName}</span>
              {' • '}
              <span className="font-mono text-xs">{conflict.filePath}</span>
            </p>
            {conflict.users.length > 0 && (
              <p className="text-sm mt-1">
                Involving: {conflict.users.join(', ')}
              </p>
            )}
            <p className="text-xs mt-2 opacity-75">
              {formatDistanceToNow(new Date(conflict.timestamp), { addSuffix: true })}
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onDismiss(conflict.id)}
          className="flex-shrink-0"
        >
          <X className="h-3 w-3" />
        </Button>
      </div>
      
      {conflict.suggestion && (
        <div className="mt-3 p-3 bg-white/50 rounded-md border">
          <div className="flex items-start space-x-2">
            <Lightbulb className="h-4 w-4 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-gray-900">Suggestion</p>
              <p className="text-sm text-gray-700 mt-1">{conflict.suggestion}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

interface ConflictAlertsProps {
  showHeader?: boolean;
  maxAlerts?: number;
}

export const ConflictAlerts: React.FC<ConflictAlertsProps> = ({ 
  showHeader = true, 
  maxAlerts = 5 
}) => {
  const { conflicts, dismissConflict, isConnected } = useRealtime();

  // Sort conflicts by severity and timestamp
  const sortedConflicts = [...conflicts]
    .sort((a, b) => {
      const severityPriority = { high: 0, medium: 1, low: 2 };
      const aPriority = severityPriority[a.severity] ?? 3;
      const bPriority = severityPriority[b.severity] ?? 3;
      
      if (aPriority !== bPriority) {
        return aPriority - bPriority;
      }
      
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    })
    .slice(0, maxAlerts);

  const highPriorityCount = conflicts.filter(c => c.severity === 'high').length;

  if (showHeader) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Conflict Alerts</span>
            <div className="flex items-center space-x-2">
              <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              {highPriorityCount > 0 && (
                <span className="text-sm font-normal text-red-600">
                  {highPriorityCount} high priority
                </span>
              )}
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {sortedConflicts.length > 0 ? (
              sortedConflicts.map((conflict) => (
                <ConflictItem 
                  key={conflict.id} 
                  conflict={conflict} 
                  onDismiss={dismissConflict}
                />
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No active conflicts</p>
                <p className="text-xs mt-1">Your team is working smoothly!</p>
                {!isConnected && (
                  <p className="text-xs mt-1 text-red-500">
                    Disconnected - conflict detection unavailable
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
      {sortedConflicts.length > 0 ? (
        sortedConflicts.map((conflict) => (
          <ConflictItem 
            key={conflict.id} 
            conflict={conflict} 
            onDismiss={dismissConflict}
          />
        ))
      ) : (
        <div className="text-center py-8 text-muted-foreground">
          <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p>No active conflicts</p>
          <p className="text-xs mt-1">Your team is working smoothly!</p>
          {!isConnected && (
            <p className="text-xs mt-1 text-red-500">
              Disconnected - conflict detection unavailable
            </p>
          )}
        </div>
      )}
    </div>
  );
};