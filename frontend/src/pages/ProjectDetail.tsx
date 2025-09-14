import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  Settings, 
  Users, 
  GitBranch, 
  Plus,
  Activity,
  Calendar,
  ExternalLink
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { RepositoryCard, type Repository } from '../components/repositories/RepositoryCard';
import { ConnectRepositoryModal, type ConnectRepositoryData } from '../components/repositories/ConnectRepositoryModal';
import { InviteMembersModal, type InviteMemberData } from '../components/projects/InviteMembersModal';
import { ActivityFeed } from '../components/realtime/ActivityFeed';
import { TeamPresence } from '../components/realtime/TeamPresence';
import type { Project } from '../components/projects/ProjectCard';

// Mock data - in a real app, this would come from an API
const mockProject: Project = {
  id: '1',
  name: 'E-commerce Platform',
  description: 'A modern e-commerce platform built with React and Node.js. Features include user authentication, product catalog, shopping cart, and payment integration.',
  ownerId: 'user-1',
  ownerName: 'John Doe',
  memberCount: 5,
  repositoryCount: 3,
  lastActivity: new Date(Date.now() - 2 * 60 * 60 * 1000),
  createdAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
  status: 'active',
  visibility: 'private',
};

const mockRepositories: Repository[] = [
  {
    id: '1',
    name: 'ecommerce-frontend',
    url: 'https://github.com/johndoe/ecommerce-frontend',
    provider: 'github',
    branch: 'main',
    projectId: '1',
    projectName: 'E-commerce Platform',
    isConnected: true,
    lastSync: new Date(Date.now() - 30 * 60 * 1000),
    deploymentUrl: 'https://ecommerce-frontend.vercel.app',
    deploymentStatus: 'success',
    visibility: 'private',
    language: 'TypeScript',
    description: 'React frontend for the e-commerce platform',
    webhookConfigured: true,
    autoDeployEnabled: true,
  },
  {
    id: '2',
    name: 'ecommerce-backend',
    url: 'https://github.com/johndoe/ecommerce-backend',
    provider: 'github',
    branch: 'main',
    projectId: '1',
    projectName: 'E-commerce Platform',
    isConnected: true,
    lastSync: new Date(Date.now() - 45 * 60 * 1000),
    deploymentUrl: 'https://ecommerce-api.railway.app',
    deploymentStatus: 'success',
    visibility: 'private',
    language: 'Node.js',
    description: 'Node.js API server for the e-commerce platform',
    webhookConfigured: true,
    autoDeployEnabled: true,
  },
  {
    id: '3',
    name: 'ecommerce-mobile',
    url: 'https://github.com/johndoe/ecommerce-mobile',
    provider: 'github',
    branch: 'develop',
    projectId: '1',
    projectName: 'E-commerce Platform',
    isConnected: false,
    lastSync: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
    deploymentStatus: 'failed',
    visibility: 'private',
    language: 'React Native',
    description: 'Mobile app for the e-commerce platform',
    webhookConfigured: false,
    autoDeployEnabled: false,
  },
];

const mockTeamMembers = [
  { id: '1', name: 'John Doe', email: 'john@example.com', role: 'owner', avatar: null },
  { id: '2', name: 'Jane Smith', email: 'jane@example.com', role: 'admin', avatar: null },
  { id: '3', name: 'Mike Johnson', email: 'mike@example.com', role: 'member', avatar: null },
  { id: '4', name: 'Sarah Chen', email: 'sarah@example.com', role: 'member', avatar: null },
  { id: '5', name: 'Alex Rodriguez', email: 'alex@example.com', role: 'member', avatar: null },
];

export const ProjectDetail: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<Project | null>(mockProject);
  const [repositories, setRepositories] = useState<Repository[]>(mockRepositories);
  const [teamMembers, setTeamMembers] = useState(mockTeamMembers);
  const [showConnectRepoModal, setShowConnectRepoModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'repositories' | 'team' | 'activity'>('overview');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // In a real app, fetch project data based on projectId
    if (!projectId) {
      navigate('/projects');
    }
  }, [projectId, navigate]);

  const handleConnectRepository = async (repositoryData: ConnectRepositoryData) => {
    setIsLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const newRepository: Repository = {
        id: Date.now().toString(),
        name: repositoryData.url.split('/').pop() || 'repository',
        url: repositoryData.url,
        provider: repositoryData.provider,
        branch: repositoryData.branch,
        projectId: project?.id || '',
        projectName: project?.name || '',
        isConnected: true,
        lastSync: new Date(),
        deploymentStatus: repositoryData.autoDeployEnabled ? 'pending' : 'none',
        visibility: 'private',
        webhookConfigured: true,
        autoDeployEnabled: repositoryData.autoDeployEnabled,
      };

      setRepositories(prev => [newRepository, ...prev]);
      
      if (project) {
        setProject(prev => prev ? { ...prev, repositoryCount: prev.repositoryCount + 1 } : null);
      }
    } catch (error) {
      console.error('Failed to connect repository:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const handleInviteMembers = async (projectId: string, members: InviteMemberData[]) => {
    setIsLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      const newMembers = members.map((member, index) => ({
        id: `new-${Date.now()}-${index}`,
        name: member.email.split('@')[0],
        email: member.email,
        role: member.role,
        avatar: null,
      }));

      setTeamMembers(prev => [...prev, ...newMembers]);
      
      if (project) {
        setProject(prev => prev ? { ...prev, memberCount: prev.memberCount + members.length } : null);
      }
    } catch (error) {
      console.error('Failed to invite members:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const handleDisconnectRepository = (repository: Repository) => {
    if (window.confirm(`Are you sure you want to disconnect "${repository.name}"?`)) {
      setRepositories(prev => prev.filter(r => r.id !== repository.id));
      if (project) {
        setProject(prev => prev ? { ...prev, repositoryCount: prev.repositoryCount - 1 } : null);
      }
    }
  };

  const handleConfigureRepository = (repository: Repository) => {
    console.log('Configure repository:', repository);
    // TODO: Implement repository configuration modal
  };

  const handleSyncRepository = async (repository: Repository) => {
    console.log('Sync repository:', repository);
    // TODO: Implement repository sync
  };

  const handleViewDeployment = (repository: Repository) => {
    if (repository.deploymentUrl) {
      window.open(repository.deploymentUrl, '_blank');
    }
  };

  if (!project) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">Project not found</h2>
          <Button onClick={() => navigate('/projects')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Projects
          </Button>
        </div>
      </div>
    );
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'repositories', label: 'Repositories', icon: GitBranch },
    { id: 'team', label: 'Team', icon: Users },
    { id: 'activity', label: 'Activity', icon: Calendar },
  ] as const;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/projects')}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold">{project.name}</h1>
            <p className="text-muted-foreground">{project.description}</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            onClick={() => setShowInviteModal(true)}
          >
            <Users className="h-4 w-4 mr-2" />
            Invite Members
          </Button>
          <Button variant="outline">
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </Button>
        </div>
      </div>

      {/* Project Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Users className="h-5 w-5 text-blue-600" />
              <div>
                <div className="text-2xl font-bold">{project.memberCount}</div>
                <div className="text-sm text-muted-foreground">Team Members</div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <GitBranch className="h-5 w-5 text-green-600" />
              <div>
                <div className="text-2xl font-bold">{project.repositoryCount}</div>
                <div className="text-sm text-muted-foreground">Repositories</div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Activity className="h-5 w-5 text-purple-600" />
              <div>
                <div className="text-2xl font-bold">
                  {repositories.filter(r => r.deploymentStatus === 'success').length}
                </div>
                <div className="text-sm text-muted-foreground">Active Deployments</div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Calendar className="h-5 w-5 text-orange-600" />
              <div>
                <div className="text-2xl font-bold">
                  {Math.floor((Date.now() - project.createdAt.getTime()) / (1000 * 60 * 60 * 24))}
                </div>
                <div className="text-sm text-muted-foreground">Days Active</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Recent Repositories</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {repositories.slice(0, 3).map((repo) => (
                      <div key={repo.id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center space-x-3">
                          <div className="text-2xl">
                            {repo.provider === 'github' ? '🐙' : repo.provider === 'gitlab' ? '🦊' : '🪣'}
                          </div>
                          <div>
                            <div className="font-medium">{repo.name}</div>
                            <div className="text-sm text-muted-foreground">{repo.branch}</div>
                          </div>
                        </div>
                        <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                          repo.deploymentStatus === 'success' ? 'bg-green-100 text-green-800' :
                          repo.deploymentStatus === 'failed' ? 'bg-red-100 text-red-800' :
                          repo.deploymentStatus === 'building' ? 'bg-blue-100 text-blue-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {repo.deploymentStatus === 'success' ? 'Deployed' :
                           repo.deploymentStatus === 'failed' ? 'Failed' :
                           repo.deploymentStatus === 'building' ? 'Building' : 'Pending'}
                        </div>
                      </div>
                    ))}
                    <Button
                      variant="outline"
                      onClick={() => setActiveTab('repositories')}
                      className="w-full"
                    >
                      View All Repositories
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <TeamPresence maxUsers={5} />
            </div>

            <div className="space-y-6">
              <ActivityFeed maxItems={6} />
            </div>
          </div>
        )}

        {activeTab === 'repositories' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">Repositories ({repositories.length})</h2>
              <Button onClick={() => setShowConnectRepoModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Connect Repository
              </Button>
            </div>

            {repositories.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-6xl mb-4">📁</div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">No repositories connected</h3>
                <p className="text-gray-500 mb-4">
                  Connect your Git repositories to enable automatic deployments and collaboration features.
                </p>
                <Button onClick={() => setShowConnectRepoModal(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Connect Repository
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {repositories.map((repository) => (
                  <RepositoryCard
                    key={repository.id}
                    repository={repository}
                    onDisconnect={handleDisconnectRepository}
                    onConfigure={handleConfigureRepository}
                    onSync={handleSyncRepository}
                    onViewDeployment={handleViewDeployment}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'team' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">Team Members ({teamMembers.length})</h2>
              <Button onClick={() => setShowInviteModal(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Invite Members
              </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {teamMembers.map((member) => (
                <Card key={member.id}>
                  <CardContent className="p-4">
                    <div className="flex items-center space-x-3">
                      <div className="h-10 w-10 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-sm font-medium text-blue-600">
                          {member.name.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div className="flex-1">
                        <div className="font-medium">{member.name}</div>
                        <div className="text-sm text-muted-foreground">{member.email}</div>
                        <div className="text-xs text-muted-foreground capitalize">{member.role}</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'activity' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ActivityFeed maxItems={10} />
            <div className="space-y-6">
              <TeamPresence maxUsers={10} />
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      <ConnectRepositoryModal
        isOpen={showConnectRepoModal}
        onClose={() => setShowConnectRepoModal(false)}
        onConnect={handleConnectRepository}
        projectId={project.id}
        projectName={project.name}
        isLoading={isLoading}
      />

      <InviteMembersModal
        isOpen={showInviteModal}
        onClose={() => setShowInviteModal(false)}
        project={project}
        onInvite={handleInviteMembers}
        isLoading={isLoading}
      />
    </div>
  );
};