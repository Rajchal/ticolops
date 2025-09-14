import React, { useState, useEffect } from 'react';
import { Plus, Search, Filter, Grid, List } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { ProjectCard, type Project } from '../components/projects/ProjectCard';
import { CreateProjectModal, type CreateProjectData } from '../components/projects/CreateProjectModal';
import { InviteMembersModal, type InviteMemberData } from '../components/projects/InviteMembersModal';
import { useAuth } from '../contexts/AuthContext';

// Mock data - in a real app, this would come from an API
const mockProjects: Project[] = [
  {
    id: '1',
    name: 'E-commerce Platform',
    description: 'A modern e-commerce platform built with React and Node.js. Features include user authentication, product catalog, shopping cart, and payment integration.',
    ownerId: 'user-1',
    ownerName: 'John Doe',
    memberCount: 5,
    repositoryCount: 3,
    lastActivity: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
    createdAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
    status: 'active',
    visibility: 'private',
  },
  {
    id: '2',
    name: 'Task Management App',
    description: 'A collaborative task management application with real-time updates, team collaboration features, and project tracking.',
    ownerId: 'user-2',
    ownerName: 'Jane Smith',
    memberCount: 3,
    repositoryCount: 2,
    lastActivity: new Date(Date.now() - 30 * 60 * 1000), // 30 minutes ago
    createdAt: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000), // 15 days ago
    status: 'active',
    visibility: 'public',
  },
  {
    id: '3',
    name: 'Weather Dashboard',
    description: 'A weather dashboard showing current conditions and forecasts with beautiful visualizations.',
    ownerId: 'user-1',
    ownerName: 'John Doe',
    memberCount: 2,
    repositoryCount: 1,
    lastActivity: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // 7 days ago
    createdAt: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000), // 45 days ago
    status: 'archived',
    visibility: 'public',
  },
  {
    id: '4',
    name: 'Blog Platform',
    description: 'A modern blogging platform with markdown support, comments, and social features.',
    ownerId: 'user-1',
    ownerName: 'John Doe',
    memberCount: 1,
    repositoryCount: 0,
    lastActivity: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000), // 1 day ago
    createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000), // 3 days ago
    status: 'draft',
    visibility: 'private',
  },
];

export const Projects: React.FC = () => {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[]>(mockProjects);
  const [filteredProjects, setFilteredProjects] = useState<Project[]>(mockProjects);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'archived' | 'draft'>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Filter projects based on search and status
  useEffect(() => {
    let filtered = projects;

    // Apply search filter
    if (searchQuery.trim()) {
      filtered = filtered.filter(project =>
        project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        project.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        project.ownerName.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(project => project.status === statusFilter);
    }

    setFilteredProjects(filtered);
  }, [projects, searchQuery, statusFilter]);

  const handleCreateProject = async (projectData: CreateProjectData) => {
    setIsLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const newProject: Project = {
        id: Date.now().toString(),
        name: projectData.name,
        description: projectData.description,
        ownerId: user?.id || 'current-user',
        ownerName: user?.name || 'Current User',
        memberCount: 1 + (projectData.initialMembers?.length || 0),
        repositoryCount: 0,
        lastActivity: new Date(),
        createdAt: new Date(),
        status: 'draft',
        visibility: projectData.visibility,
      };

      setProjects(prev => [newProject, ...prev]);
    } catch (error) {
      console.error('Failed to create project:', error);
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
      
      // Update project member count
      setProjects(prev => prev.map(project =>
        project.id === projectId
          ? { ...project, memberCount: project.memberCount + members.length }
          : project
      ));
    } catch (error) {
      console.error('Failed to invite members:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditProject = (project: Project) => {
    console.log('Edit project:', project);
    // TODO: Implement edit project modal
  };

  const handleDeleteProject = (project: Project) => {
    if (window.confirm(`Are you sure you want to delete "${project.name}"? This action cannot be undone.`)) {
      setProjects(prev => prev.filter(p => p.id !== project.id));
    }
  };

  const handleInviteMembersClick = (project: Project) => {
    setSelectedProject(project);
    setShowInviteModal(true);
  };

  const handleViewProject = (project: Project) => {
    // TODO: Navigate to project detail page
    console.log('View project:', project);
  };

  const myProjects = filteredProjects.filter(p => p.ownerId === user?.id);
  const sharedProjects = filteredProjects.filter(p => p.ownerId !== user?.id);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Projects</h1>
          <p className="text-muted-foreground">
            Manage your projects and collaborate with your team
          </p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Project
        </Button>
      </div>

      {/* Filters and Search */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex flex-col sm:flex-row gap-4 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
            <Input
              type="text"
              placeholder="Search projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          
          <div className="flex items-center space-x-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="draft">Draft</option>
              <option value="archived">Archived</option>
            </select>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant={viewMode === 'grid' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('grid')}
          >
            <Grid className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === 'list' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewMode('list')}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-2xl font-bold text-blue-600">{projects.length}</div>
          <div className="text-sm text-muted-foreground">Total Projects</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-2xl font-bold text-green-600">
            {projects.filter(p => p.status === 'active').length}
          </div>
          <div className="text-sm text-muted-foreground">Active Projects</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-2xl font-bold text-purple-600">{myProjects.length}</div>
          <div className="text-sm text-muted-foreground">My Projects</div>
        </div>
        <div className="bg-white p-4 rounded-lg border">
          <div className="text-2xl font-bold text-orange-600">{sharedProjects.length}</div>
          <div className="text-sm text-muted-foreground">Shared Projects</div>
        </div>
      </div>

      {/* Projects List */}
      {filteredProjects.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">📁</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {searchQuery || statusFilter !== 'all' ? 'No projects found' : 'No projects yet'}
          </h3>
          <p className="text-gray-500 mb-4">
            {searchQuery || statusFilter !== 'all'
              ? 'Try adjusting your search or filters'
              : 'Get started by creating your first project'
            }
          </p>
          {!searchQuery && statusFilter === 'all' && (
            <Button onClick={() => setShowCreateModal(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Project
            </Button>
          )}
        </div>
      ) : (
        <div className="space-y-8">
          {/* My Projects */}
          {myProjects.length > 0 && (
            <div>
              <h2 className="text-xl font-semibold mb-4">My Projects ({myProjects.length})</h2>
              <div className={`grid gap-6 ${
                viewMode === 'grid' 
                  ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' 
                  : 'grid-cols-1'
              }`}>
                {myProjects.map((project) => (
                  <ProjectCard
                    key={project.id}
                    project={project}
                    onEdit={handleEditProject}
                    onDelete={handleDeleteProject}
                    onInviteMembers={handleInviteMembersClick}
                    onViewProject={handleViewProject}
                    isOwner={true}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Shared Projects */}
          {sharedProjects.length > 0 && (
            <div>
              <h2 className="text-xl font-semibold mb-4">Shared Projects ({sharedProjects.length})</h2>
              <div className={`grid gap-6 ${
                viewMode === 'grid' 
                  ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' 
                  : 'grid-cols-1'
              }`}>
                {sharedProjects.map((project) => (
                  <ProjectCard
                    key={project.id}
                    project={project}
                    onViewProject={handleViewProject}
                    isOwner={false}
                    showActions={false}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      <CreateProjectModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={handleCreateProject}
        isLoading={isLoading}
      />

      <InviteMembersModal
        isOpen={showInviteModal}
        onClose={() => {
          setShowInviteModal(false);
          setSelectedProject(null);
        }}
        project={selectedProject}
        onInvite={handleInviteMembers}
        isLoading={isLoading}
      />
    </div>
  );
};