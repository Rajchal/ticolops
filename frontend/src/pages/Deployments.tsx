import React, { useState, useEffect } from 'react';
import { Search, Filter, RefreshCw, Calendar, GitBranch, Eye, Download } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { DeploymentCard, type Deployment } from '../components/deployments/DeploymentCard';
import { DeploymentLogsModal } from '../components/deployments/DeploymentLogsModal';
import { PreviewModal } from '../components/deployments/PreviewModal';
import { useAuth } from '../contexts/AuthContext';

// Mock data - in a real app, this would come from an API
const mockDeployments: Deployment[] = [
  {
    id: '1',
    repositoryId: 'repo-1',
    repositoryName: 'ecommerce-frontend',
    projectId: 'project-1',
    projectName: 'E-commerce Platform',
    branch: 'main',
    commitHash: 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0',
    commitMessage: 'Add shopping cart functionality and payment integration',
    author: 'John Doe',
    status: 'success',
    url: 'https://ecommerce-frontend-abc123.vercel.app',
    previewUrl: 'https://ecommerce-frontend-abc123.vercel.app',
    buildDuration: 145,
    startedAt: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
    completedAt: new Date(Date.now() - 2 * 60 * 60 * 1000 + 145 * 1000),
    logs: [
      '[2024-01-15T10:00:00Z] [INFO] Starting build process...',
      '[2024-01-15T10:00:05Z] [INFO] Installing dependencies...',
      '[2024-01-15T10:00:30Z] [INFO] Running npm install...',
      '[2024-01-15T10:01:00Z] [INFO] Dependencies installed successfully',
      '[2024-01-15T10:01:05Z] [INFO] Running build command: npm run build',
      '[2024-01-15T10:01:10Z] [INFO] Building React application...',
      '[2024-01-15T10:02:00Z] [INFO] Optimizing bundle size...',
      '[2024-01-15T10:02:20Z] [INFO] Build completed successfully',
      '[2024-01-15T10:02:25Z] [INFO] Deploying to production...',
      '[2024-01-15T10:02:30Z] [INFO] Deployment successful!',
    ],
    buildCommand: 'npm run build',
    environment: 'production',
  },
  {
    id: '2',
    repositoryId: 'repo-2',
    repositoryName: 'ecommerce-backend',
    projectId: 'project-1',
    projectName: 'E-commerce Platform',
    branch: 'develop',
    commitHash: 'b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1',
    commitMessage: 'Update API endpoints for user authentication',
    author: 'Jane Smith',
    status: 'building',
    buildDuration: 67,
    startedAt: new Date(Date.now() - 5 * 60 * 1000), // 5 minutes ago
    logs: [
      '[2024-01-15T14:25:00Z] [INFO] Starting build process...',
      '[2024-01-15T14:25:05Z] [INFO] Installing dependencies...',
      '[2024-01-15T14:25:30Z] [INFO] Running pip install -r requirements.txt',
      '[2024-01-15T14:26:00Z] [INFO] Dependencies installed successfully',
      '[2024-01-15T14:26:05Z] [INFO] Running tests...',
      '[2024-01-15T14:26:30Z] [INFO] All tests passed',
      '[2024-01-15T14:26:35Z] [INFO] Building Docker image...',
    ],
    buildCommand: 'docker build -t api .',
    environment: 'staging',
  },
  {
    id: '3',
    repositoryId: 'repo-3',
    repositoryName: 'task-manager-app',
    projectId: 'project-2',
    projectName: 'Task Management App',
    branch: 'main',
    commitHash: 'c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2',
    commitMessage: 'Fix critical bug in task deletion',
    author: 'Mike Johnson',
    status: 'failed',
    buildDuration: 89,
    startedAt: new Date(Date.now() - 30 * 60 * 1000), // 30 minutes ago
    completedAt: new Date(Date.now() - 30 * 60 * 1000 + 89 * 1000),
    logs: [
      '[2024-01-15T14:00:00Z] [INFO] Starting build process...',
      '[2024-01-15T14:00:05Z] [INFO] Installing dependencies...',
      '[2024-01-15T14:00:30Z] [INFO] Running npm install...',
      '[2024-01-15T14:01:00Z] [ERROR] Failed to install dependencies',
      '[2024-01-15T14:01:05Z] [ERROR] Package @types/node@18.0.0 not found',
      '[2024-01-15T14:01:10Z] [ERROR] Build failed with exit code 1',
    ],
    errorMessage: 'Build failed due to missing dependencies. Package @types/node@18.0.0 could not be found.',
    buildCommand: 'npm run build',
    environment: 'production',
  },
  {
    id: '4',
    repositoryId: 'repo-4',
    repositoryName: 'blog-platform',
    projectId: 'project-3',
    projectName: 'Blog Platform',
    branch: 'feature/comments',
    commitHash: 'd4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3',
    commitMessage: 'Add comment system with moderation',
    author: 'Sarah Chen',
    status: 'pending',
    startedAt: new Date(Date.now() - 2 * 60 * 1000), // 2 minutes ago
    logs: [
      '[2024-01-15T14:28:00Z] [INFO] Deployment queued...',
      '[2024-01-15T14:28:05Z] [INFO] Waiting for available build slot...',
    ],
    buildCommand: 'npm run build',
    environment: 'development',
  },
];

export const Deployments: React.FC = () => {
  const { user } = useAuth();
  const [deployments, setDeployments] = useState<Deployment[]>(mockDeployments);
  const [filteredDeployments, setFilteredDeployments] = useState<Deployment[]>(mockDeployments);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | Deployment['status']>('all');
  const [environmentFilter, setEnvironmentFilter] = useState<'all' | Deployment['environment']>('all');
  const [selectedDeployment, setSelectedDeployment] = useState<Deployment | null>(null);
  const [showLogsModal, setShowLogsModal] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Filter deployments based on search and filters
  useEffect(() => {
    let filtered = deployments;

    // Apply search filter
    if (searchQuery.trim()) {
      filtered = filtered.filter(deployment =>
        deployment.repositoryName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        deployment.projectName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        deployment.commitMessage.toLowerCase().includes(searchQuery.toLowerCase()) ||
        deployment.author.toLowerCase().includes(searchQuery.toLowerCase()) ||
        deployment.branch.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(deployment => deployment.status === statusFilter);
    }

    // Apply environment filter
    if (environmentFilter !== 'all') {
      filtered = filtered.filter(deployment => deployment.environment === environmentFilter);
    }

    setFilteredDeployments(filtered);
  }, [deployments, searchQuery, statusFilter, environmentFilter]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      // In a real app, this would fetch fresh data from the API
      console.log('Refreshing deployments...');
    } catch (error) {
      console.error('Failed to refresh deployments:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleViewLogs = (deployment: Deployment) => {
    setSelectedDeployment(deployment);
    setShowLogsModal(true);
  };

  const handleViewPreview = (deployment: Deployment) => {
    setSelectedDeployment(deployment);
    setShowPreviewModal(true);
  };

  const handleRetryDeployment = async (deployment: Deployment) => {
    try {
      // Simulate API call to retry deployment
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Update deployment status
      setDeployments(prev => prev.map(d =>
        d.id === deployment.id
          ? { ...d, status: 'pending', startedAt: new Date() }
          : d
      ));
    } catch (error) {
      console.error('Failed to retry deployment:', error);
    }
  };

  const handleCancelDeployment = async (deployment: Deployment) => {
    if (!window.confirm('Are you sure you want to cancel this deployment?')) {
      return;
    }

    try {
      // Simulate API call to cancel deployment
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Update deployment status
      setDeployments(prev => prev.map(d =>
        d.id === deployment.id
          ? { ...d, status: 'cancelled', completedAt: new Date() }
          : d
      ));
    } catch (error) {
      console.error('Failed to cancel deployment:', error);
    }
  };

  const handleRefreshLogs = async (deployment: Deployment) => {
    // Simulate fetching fresh logs
    console.log('Refreshing logs for deployment:', deployment.id);
  };

  // Stats calculations
  const totalDeployments = deployments.length;
  const successfulDeployments = deployments.filter(d => d.status === 'success').length;
  const failedDeployments = deployments.filter(d => d.status === 'failed').length;
  const activeDeployments = deployments.filter(d => d.status === 'building' || d.status === 'pending').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Deployments</h1>
          <p className="text-muted-foreground">
            Monitor your application deployments and preview live versions
          </p>
        </div>
        <Button onClick={handleRefresh} disabled={isRefreshing}>
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Calendar className="h-5 w-5 text-blue-600" />
              <div>
                <div className="text-2xl font-bold">{totalDeployments}</div>
                <div className="text-sm text-muted-foreground">Total Deployments</div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <div className="h-5 w-5 bg-green-500 rounded-full"></div>
              <div>
                <div className="text-2xl font-bold text-green-600">{successfulDeployments}</div>
                <div className="text-sm text-muted-foreground">Successful</div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <div className="h-5 w-5 bg-red-500 rounded-full"></div>
              <div>
                <div className="text-2xl font-bold text-red-600">{failedDeployments}</div>
                <div className="text-sm text-muted-foreground">Failed</div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <div className="h-5 w-5 bg-blue-500 rounded-full animate-pulse"></div>
              <div>
                <div className="text-2xl font-bold text-blue-600">{activeDeployments}</div>
                <div className="text-sm text-muted-foreground">In Progress</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex flex-col sm:flex-row gap-4 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
            <Input
              type="text"
              placeholder="Search deployments..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="success">Success</option>
                <option value="failed">Failed</option>
                <option value="building">Building</option>
                <option value="pending">Pending</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            
            <select
              value={environmentFilter}
              onChange={(e) => setEnvironmentFilter(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Environments</option>
              <option value="production">Production</option>
              <option value="staging">Staging</option>
              <option value="development">Development</option>
            </select>
          </div>
        </div>
      </div>

      {/* Deployments List */}
      {filteredDeployments.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">🚀</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {searchQuery || statusFilter !== 'all' || environmentFilter !== 'all' 
              ? 'No deployments found' 
              : 'No deployments yet'
            }
          </h3>
          <p className="text-gray-500 mb-4">
            {searchQuery || statusFilter !== 'all' || environmentFilter !== 'all'
              ? 'Try adjusting your search or filters'
              : 'Deployments will appear here when you connect repositories and push code'
            }
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredDeployments.map((deployment) => (
            <DeploymentCard
              key={deployment.id}
              deployment={deployment}
              onViewLogs={handleViewLogs}
              onViewPreview={handleViewPreview}
              onRetry={handleRetryDeployment}
              onCancel={handleCancelDeployment}
            />
          ))}
        </div>
      )}

      {/* Modals */}
      <DeploymentLogsModal
        isOpen={showLogsModal}
        onClose={() => {
          setShowLogsModal(false);
          setSelectedDeployment(null);
        }}
        deployment={selectedDeployment}
        onRefresh={handleRefreshLogs}
      />

      <PreviewModal
        isOpen={showPreviewModal}
        onClose={() => {
          setShowPreviewModal(false);
          setSelectedDeployment(null);
        }}
        deployment={selectedDeployment}
      />
    </div>
  );
};