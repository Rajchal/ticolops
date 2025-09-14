import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { 
  GitBranch, 
  ExternalLink, 
  Settings, 
  AlertCircle,
  CheckCircle,
  Clock,
  Trash2,
  RefreshCw,
  Globe,
  Lock
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';

export interface Repository {
  id: string;
  name: string;
  url: string;
  provider: 'github' | 'gitlab' | 'bitbucket';
  branch: string;
  projectId: string;
  projectName: string;
  isConnected: boolean;
  lastSync: Date;
  deploymentUrl?: string;
  deploymentStatus: 'pending' | 'building' | 'success' | 'failed' | 'none';
  visibility: 'public' | 'private';
  language?: string;
  description?: string;
  webhookConfigured: boolean;
  autoDeployEnabled: boolean;
}

interface RepositoryCardProps {
  repository: Repository;
  onDisconnect?: (repository: Repository) => void;
  onConfigure?: (repository: Repository) => void;
  onSync?: (repository: Repository) => void;
  onViewDeployment?: (repository: Repository) => void;
  showActions?: boolean;
}

const getProviderIcon = (provider: Repository['provider']) => {
  switch (provider) {
    case 'github':
      return '🐙'; // GitHub icon
    case 'gitlab':
      return '🦊'; // GitLab icon
    case 'bitbucket':
      return '🪣'; // Bitbucket icon
    default:
      return '📁';
  }
};

const getDeploymentStatusColor = (status: Repository['deploymentStatus']) => {
  switch (status) {
    case 'success':
      return 'text-green-600 bg-green-100';
    case 'failed':
      return 'text-red-600 bg-red-100';
    case 'building':
      return 'text-blue-600 bg-blue-100';
    case 'pending':
      return 'text-yellow-600 bg-yellow-100';
    case 'none':
      return 'text-gray-600 bg-gray-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
};

const getDeploymentStatusText = (status: Repository['deploymentStatus']) => {
  switch (status) {
    case 'success':
      return 'Deployed';
    case 'failed':
      return 'Failed';
    case 'building':
      return 'Building';
    case 'pending':
      return 'Pending';
    case 'none':
      return 'Not deployed';
    default:
      return 'Unknown';
  }
};

const getDeploymentStatusIcon = (status: Repository['deploymentStatus']) => {
  switch (status) {
    case 'success':
      return <CheckCircle className="h-4 w-4" />;
    case 'failed':
      return <AlertCircle className="h-4 w-4" />;
    case 'building':
      return <RefreshCw className="h-4 w-4 animate-spin" />;
    case 'pending':
      return <Clock className="h-4 w-4" />;
    case 'none':
      return <Clock className="h-4 w-4" />;
    default:
      return <Clock className="h-4 w-4" />;
  }
};

export const RepositoryCard: React.FC<RepositoryCardProps> = ({
  repository,
  onDisconnect,
  onConfigure,
  onSync,
  onViewDeployment,
  showActions = true,
}) => {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg font-semibold text-foreground flex items-center space-x-2">
              <span>{getProviderIcon(repository.provider)}</span>
              <span>{repository.name}</span>
              {repository.visibility === 'private' ? (
                <Lock className="h-4 w-4 text-gray-500" />
              ) : (
                <Globe className="h-4 w-4 text-gray-500" />
              )}
            </CardTitle>
            <div className="flex items-center space-x-2 mt-1">
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                repository.isConnected 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-red-100 text-red-800'
              }`}>
                {repository.isConnected ? 'Connected' : 'Disconnected'}
              </span>
              <span className="text-xs text-muted-foreground">
                {repository.provider.charAt(0).toUpperCase() + repository.provider.slice(1)}
              </span>
            </div>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        {repository.description && (
          <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
            {repository.description}
          </p>
        )}
        
        <div className="space-y-3">
          {/* Repository Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              <GitBranch className="h-4 w-4" />
              <span>{repository.branch}</span>
            </div>
            
            {repository.language && (
              <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                <div className="h-3 w-3 bg-blue-500 rounded-full"></div>
                <span>{repository.language}</span>
              </div>
            )}
          </div>

          {/* Deployment Status */}
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-2">
              <div className={`flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium ${getDeploymentStatusColor(repository.deploymentStatus)}`}>
                {getDeploymentStatusIcon(repository.deploymentStatus)}
                <span>{getDeploymentStatusText(repository.deploymentStatus)}</span>
              </div>
            </div>
            
            {repository.deploymentUrl && repository.deploymentStatus === 'success' && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onViewDeployment?.(repository)}
                className="text-xs"
              >
                <ExternalLink className="h-3 w-3 mr-1" />
                View Live
              </Button>
            )}
          </div>

          {/* Configuration Status */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Webhook:</span>
              <span className={`flex items-center space-x-1 ${
                repository.webhookConfigured ? 'text-green-600' : 'text-red-600'
              }`}>
                {repository.webhookConfigured ? (
                  <CheckCircle className="h-3 w-3" />
                ) : (
                  <AlertCircle className="h-3 w-3" />
                )}
                <span>{repository.webhookConfigured ? 'Configured' : 'Not configured'}</span>
              </span>
            </div>
            
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Auto Deploy:</span>
              <span className={`flex items-center space-x-1 ${
                repository.autoDeployEnabled ? 'text-green-600' : 'text-gray-600'
              }`}>
                {repository.autoDeployEnabled ? (
                  <CheckCircle className="h-3 w-3" />
                ) : (
                  <Clock className="h-3 w-3" />
                )}
                <span>{repository.autoDeployEnabled ? 'Enabled' : 'Disabled'}</span>
              </span>
            </div>
          </div>

          {/* Last Sync */}
          <div className="text-xs text-muted-foreground">
            Last synced {formatDistanceToNow(new Date(repository.lastSync), { addSuffix: true })}
          </div>

          {/* Project Info */}
          <div className="text-xs text-muted-foreground">
            Project: {repository.projectName}
          </div>
        </div>
        
        {showActions && (
          <div className="mt-4 pt-4 border-t space-y-2">
            <div className="flex space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onSync?.(repository)}
                className="flex-1"
                disabled={!repository.isConnected}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Sync
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => onConfigure?.(repository)}
                className="flex-1"
              >
                <Settings className="h-4 w-4 mr-2" />
                Configure
              </Button>
            </div>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.open(repository.url, '_blank')}
              className="w-full"
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              View on {repository.provider.charAt(0).toUpperCase() + repository.provider.slice(1)}
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => onDisconnect?.(repository)}
              className="w-full text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Disconnect Repository
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};