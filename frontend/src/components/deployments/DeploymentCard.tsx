import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { 
  ExternalLink, 
  Clock, 
  CheckCircle, 
  AlertCircle, 
  RefreshCw,
  GitCommit,
  User,
  Calendar,
  Eye,
  Download,
  RotateCcw
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';

export interface Deployment {
  id: string;
  repositoryId: string;
  repositoryName: string;
  projectId: string;
  projectName: string;
  branch: string;
  commitHash: string;
  commitMessage: string;
  author: string;
  status: 'pending' | 'building' | 'success' | 'failed' | 'cancelled';
  url?: string;
  previewUrl?: string;
  buildDuration?: number; // in seconds
  startedAt: Date;
  completedAt?: Date;
  logs: string[];
  errorMessage?: string;
  buildCommand?: string;
  environment: 'development' | 'staging' | 'production';
}

interface DeploymentCardProps {
  deployment: Deployment;
  onViewLogs?: (deployment: Deployment) => void;
  onViewPreview?: (deployment: Deployment) => void;
  onRetry?: (deployment: Deployment) => void;
  onCancel?: (deployment: Deployment) => void;
  showActions?: boolean;
  compact?: boolean;
}

const getStatusColor = (status: Deployment['status']) => {
  switch (status) {
    case 'success':
      return 'text-green-600 bg-green-100 border-green-200';
    case 'failed':
      return 'text-red-600 bg-red-100 border-red-200';
    case 'building':
      return 'text-blue-600 bg-blue-100 border-blue-200';
    case 'pending':
      return 'text-yellow-600 bg-yellow-100 border-yellow-200';
    case 'cancelled':
      return 'text-gray-600 bg-gray-100 border-gray-200';
    default:
      return 'text-gray-600 bg-gray-100 border-gray-200';
  }
};

const getStatusIcon = (status: Deployment['status']) => {
  switch (status) {
    case 'success':
      return <CheckCircle className="h-4 w-4" />;
    case 'failed':
      return <AlertCircle className="h-4 w-4" />;
    case 'building':
      return <RefreshCw className="h-4 w-4 animate-spin" />;
    case 'pending':
      return <Clock className="h-4 w-4" />;
    case 'cancelled':
      return <AlertCircle className="h-4 w-4" />;
    default:
      return <Clock className="h-4 w-4" />;
  }
};

const getStatusText = (status: Deployment['status']) => {
  switch (status) {
    case 'success':
      return 'Deployed';
    case 'failed':
      return 'Failed';
    case 'building':
      return 'Building';
    case 'pending':
      return 'Pending';
    case 'cancelled':
      return 'Cancelled';
    default:
      return 'Unknown';
  }
};

const getEnvironmentColor = (environment: Deployment['environment']) => {
  switch (environment) {
    case 'production':
      return 'bg-red-100 text-red-800';
    case 'staging':
      return 'bg-yellow-100 text-yellow-800';
    case 'development':
      return 'bg-blue-100 text-blue-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

const formatDuration = (seconds: number): string => {
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
};

export const DeploymentCard: React.FC<DeploymentCardProps> = ({
  deployment,
  onViewLogs,
  onViewPreview,
  onRetry,
  onCancel,
  showActions = true,
  compact = false,
}) => {
  const isInProgress = deployment.status === 'building' || deployment.status === 'pending';
  const canRetry = deployment.status === 'failed' || deployment.status === 'cancelled';
  const canCancel = deployment.status === 'building' || deployment.status === 'pending';
  const hasPreview = deployment.status === 'success' && (deployment.url || deployment.previewUrl);

  if (compact) {
    return (
      <div className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50">
        <div className="flex items-center space-x-3">
          <div className={`flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(deployment.status)}`}>
            {getStatusIcon(deployment.status)}
            <span>{getStatusText(deployment.status)}</span>
          </div>
          
          <div>
            <div className="font-medium text-sm">{deployment.repositoryName}</div>
            <div className="text-xs text-muted-foreground">
              {deployment.commitHash.substring(0, 7)} • {deployment.branch}
            </div>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <span className="text-xs text-muted-foreground">
            {formatDistanceToNow(new Date(deployment.startedAt), { addSuffix: true })}
          </span>
          
          {hasPreview && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => onViewPreview?.(deployment)}
              className="h-6 px-2 text-xs"
            >
              <Eye className="h-3 w-3 mr-1" />
              Preview
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg font-semibold text-foreground flex items-center space-x-2">
              <span>{deployment.repositoryName}</span>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getEnvironmentColor(deployment.environment)}`}>
                {deployment.environment}
              </span>
            </CardTitle>
            <div className="flex items-center space-x-2 mt-1">
              <div className={`flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(deployment.status)}`}>
                {getStatusIcon(deployment.status)}
                <span>{getStatusText(deployment.status)}</span>
              </div>
            </div>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="space-y-4">
          {/* Commit Information */}
          <div className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg">
            <GitCommit className="h-4 w-4 text-muted-foreground mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2">
                <span className="font-mono text-sm font-medium">{deployment.commitHash.substring(0, 7)}</span>
                <span className="text-sm text-muted-foreground">on {deployment.branch}</span>
              </div>
              <p className="text-sm text-muted-foreground mt-1 truncate">
                {deployment.commitMessage}
              </p>
              <div className="flex items-center space-x-4 mt-2 text-xs text-muted-foreground">
                <div className="flex items-center space-x-1">
                  <User className="h-3 w-3" />
                  <span>{deployment.author}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Calendar className="h-3 w-3" />
                  <span>{formatDistanceToNow(new Date(deployment.startedAt), { addSuffix: true })}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Build Information */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Started:</span>
              <div className="font-medium">
                {new Date(deployment.startedAt).toLocaleString()}
              </div>
            </div>
            
            {deployment.completedAt && (
              <div>
                <span className="text-muted-foreground">Completed:</span>
                <div className="font-medium">
                  {new Date(deployment.completedAt).toLocaleString()}
                </div>
              </div>
            )}
            
            {deployment.buildDuration && (
              <div>
                <span className="text-muted-foreground">Duration:</span>
                <div className="font-medium">
                  {formatDuration(deployment.buildDuration)}
                </div>
              </div>
            )}
            
            {deployment.buildCommand && (
              <div>
                <span className="text-muted-foreground">Build Command:</span>
                <div className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                  {deployment.buildCommand}
                </div>
              </div>
            )}
          </div>

          {/* Error Message */}
          {deployment.errorMessage && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start space-x-2">
                <AlertCircle className="h-4 w-4 text-red-600 mt-0.5" />
                <div>
                  <h4 className="text-sm font-medium text-red-800">Deployment Failed</h4>
                  <p className="text-sm text-red-700 mt-1">{deployment.errorMessage}</p>
                </div>
              </div>
            </div>
          )}

          {/* Preview URL */}
          {hasPreview && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-medium text-green-800">Deployment Ready</h4>
                  <p className="text-sm text-green-700 mt-1">
                    Your application is live and ready to view
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onViewPreview?.(deployment)}
                  className="text-green-700 border-green-300 hover:bg-green-100"
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  View Live
                </Button>
              </div>
            </div>
          )}

          {/* Progress Indicator */}
          {isInProgress && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Building...</span>
                <span className="text-muted-foreground">
                  {deployment.buildDuration ? formatDuration(deployment.buildDuration) : 'Starting...'}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '60%' }}></div>
              </div>
            </div>
          )}
        </div>
        
        {showActions && (
          <div className="mt-4 pt-4 border-t space-y-2">
            <div className="flex space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onViewLogs?.(deployment)}
                className="flex-1"
              >
                <Download className="h-4 w-4 mr-2" />
                View Logs
              </Button>
              
              {canRetry && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onRetry?.(deployment)}
                  className="flex-1"
                >
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Retry
                </Button>
              )}
              
              {canCancel && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onCancel?.(deployment)}
                  className="flex-1 text-red-600 hover:text-red-700 hover:bg-red-50"
                >
                  Cancel
                </Button>
              )}
            </div>
            
            {hasPreview && (
              <Button
                variant="default"
                size="sm"
                onClick={() => onViewPreview?.(deployment)}
                className="w-full"
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                Open Preview
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};