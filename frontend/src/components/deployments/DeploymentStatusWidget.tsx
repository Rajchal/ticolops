import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { 
  CheckCircle, 
  AlertCircle, 
  RefreshCw, 
  Clock, 
  ExternalLink,
  Eye,
  TrendingUp,
  TrendingDown
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';
import type { Deployment } from './DeploymentCard';

interface DeploymentStatusWidgetProps {
  deployments: Deployment[];
  onViewAll?: () => void;
  onViewPreview?: (deployment: Deployment) => void;
  showTrends?: boolean;
  maxItems?: number;
}

const getStatusIcon = (status: Deployment['status']) => {
  switch (status) {
    case 'success':
      return <CheckCircle className="h-4 w-4 text-green-600" />;
    case 'failed':
      return <AlertCircle className="h-4 w-4 text-red-600" />;
    case 'building':
      return <RefreshCw className="h-4 w-4 text-blue-600 animate-spin" />;
    case 'pending':
      return <Clock className="h-4 w-4 text-yellow-600" />;
    case 'cancelled':
      return <AlertCircle className="h-4 w-4 text-gray-600" />;
    default:
      return <Clock className="h-4 w-4 text-gray-600" />;
  }
};

const getStatusColor = (status: Deployment['status']) => {
  switch (status) {
    case 'success':
      return 'text-green-600';
    case 'failed':
      return 'text-red-600';
    case 'building':
      return 'text-blue-600';
    case 'pending':
      return 'text-yellow-600';
    case 'cancelled':
      return 'text-gray-600';
    default:
      return 'text-gray-600';
  }
};

export const DeploymentStatusWidget: React.FC<DeploymentStatusWidgetProps> = ({
  deployments,
  onViewAll,
  onViewPreview,
  showTrends = true,
  maxItems = 5,
}) => {
  const recentDeployments = deployments
    .sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime())
    .slice(0, maxItems);

  const activeDeployments = deployments.filter(d => 
    d.status === 'building' || d.status === 'pending'
  ).length;

  const successRate = deployments.length > 0 
    ? Math.round((deployments.filter(d => d.status === 'success').length / deployments.length) * 100)
    : 0;

  // Calculate trend (comparing last 7 days vs previous 7 days)
  const now = new Date();
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const fourteenDaysAgo = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000);

  const recentSuccessful = deployments.filter(d => 
    d.status === 'success' && 
    new Date(d.startedAt) >= sevenDaysAgo
  ).length;

  const previousSuccessful = deployments.filter(d => 
    d.status === 'success' && 
    new Date(d.startedAt) >= fourteenDaysAgo && 
    new Date(d.startedAt) < sevenDaysAgo
  ).length;

  const trend = previousSuccessful > 0 
    ? ((recentSuccessful - previousSuccessful) / previousSuccessful) * 100
    : recentSuccessful > 0 ? 100 : 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="text-lg font-semibold">Deployment Status</CardTitle>
        {onViewAll && (
          <Button variant="outline" size="sm" onClick={onViewAll}>
            View All
          </Button>
        )}
      </CardHeader>
      
      <CardContent>
        <div className="space-y-4">
          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{deployments.length}</div>
              <div className="text-xs text-muted-foreground">Total</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{successRate}%</div>
              <div className="text-xs text-muted-foreground">Success Rate</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">{activeDeployments}</div>
              <div className="text-xs text-muted-foreground">Active</div>
            </div>
          </div>

          {/* Trend Indicator */}
          {showTrends && (
            <div className="flex items-center justify-center space-x-2 text-sm">
              {trend > 0 ? (
                <>
                  <TrendingUp className="h-4 w-4 text-green-600" />
                  <span className="text-green-600">+{trend.toFixed(1)}% this week</span>
                </>
              ) : trend < 0 ? (
                <>
                  <TrendingDown className="h-4 w-4 text-red-600" />
                  <span className="text-red-600">{trend.toFixed(1)}% this week</span>
                </>
              ) : (
                <span className="text-muted-foreground">No change this week</span>
              )}
            </div>
          )}

          {/* Recent Deployments */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-muted-foreground">Recent Deployments</h4>
            {recentDeployments.length === 0 ? (
              <div className="text-center py-4 text-muted-foreground">
                <div className="text-4xl mb-2">🚀</div>
                <p className="text-sm">No deployments yet</p>
              </div>
            ) : (
              <div className="space-y-2">
                {recentDeployments.map((deployment) => (
                  <div
                    key={deployment.id}
                    className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center space-x-3 flex-1 min-w-0">
                      {getStatusIcon(deployment.status)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-medium truncate">
                            {deployment.repositoryName}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {deployment.branch}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(deployment.startedAt), { addSuffix: true })}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-1">
                      {deployment.status === 'success' && (deployment.url || deployment.previewUrl) && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onViewPreview?.(deployment)}
                          className="h-6 px-2 text-xs"
                        >
                          <Eye className="h-3 w-3" />
                        </Button>
                      )}
                      
                      <div className={`text-xs font-medium ${getStatusColor(deployment.status)}`}>
                        {deployment.status === 'success' && '✓'}
                        {deployment.status === 'failed' && '✗'}
                        {deployment.status === 'building' && '⟳'}
                        {deployment.status === 'pending' && '⏳'}
                        {deployment.status === 'cancelled' && '⊘'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Active Deployments Alert */}
          {activeDeployments > 0 && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center space-x-2">
                <RefreshCw className="h-4 w-4 text-blue-600 animate-spin" />
                <div>
                  <p className="text-sm font-medium text-blue-800">
                    {activeDeployments} deployment{activeDeployments > 1 ? 's' : ''} in progress
                  </p>
                  <p className="text-xs text-blue-700">
                    Check the deployments page for detailed status
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Quick Actions */}
          {onViewAll && (
            <div className="pt-2 border-t">
              <Button
                variant="outline"
                size="sm"
                onClick={onViewAll}
                className="w-full"
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                View All Deployments
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};