import React from 'react';
import { WifiOff, AlertCircle, CheckCircle } from 'lucide-react';
import { useRealtime } from '../../contexts/RealtimeContext';

interface ConnectionStatusProps {
  showText?: boolean;
  className?: string;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ 
  showText = false, 
  className = '' 
}) => {
  const { isConnected, connectionError } = useRealtime();

  if (connectionError) {
    return (
      <div className={`flex items-center space-x-2 text-red-600 ${className}`}>
        <AlertCircle className="h-4 w-4" />
        {showText && <span className="text-sm">Connection Error</span>}
      </div>
    );
  }

  if (isConnected) {
    return (
      <div className={`flex items-center space-x-2 text-green-600 ${className}`}>
        <CheckCircle className="h-4 w-4" />
        {showText && <span className="text-sm">Connected</span>}
      </div>
    );
  }

  return (
    <div className={`flex items-center space-x-2 text-yellow-600 ${className}`}>
      <WifiOff className="h-4 w-4" />
      {showText && <span className="text-sm">Connecting...</span>}
    </div>
  );
};

interface DetailedConnectionStatusProps {
  className?: string;
}

export const DetailedConnectionStatus: React.FC<DetailedConnectionStatusProps> = ({ 
  className = '' 
}) => {
  const { isConnected, connectionError, activities, userPresence } = useRealtime();

  return (
    <div className={`p-4 bg-card border rounded-lg ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium">Real-time Status</h3>
        <ConnectionStatus showText />
      </div>
      
      <div className="space-y-2 text-sm text-muted-foreground">
        <div className="flex justify-between">
          <span>Connection:</span>
          <span className={isConnected ? 'text-green-600' : 'text-red-600'}>
            {isConnected ? 'Active' : 'Disconnected'}
          </span>
        </div>
        
        <div className="flex justify-between">
          <span>Recent Activities:</span>
          <span>{activities.length}</span>
        </div>
        
        <div className="flex justify-between">
          <span>Team Members:</span>
          <span>{userPresence.length}</span>
        </div>
        
        <div className="flex justify-between">
          <span>Online Now:</span>
          <span className="text-green-600">
            {userPresence.filter(u => u.status === 'online' || u.status === 'busy').length}
          </span>
        </div>
        
        {connectionError && (
          <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-xs">
            <strong>Error:</strong> {connectionError}
          </div>
        )}
      </div>
    </div>
  );
};