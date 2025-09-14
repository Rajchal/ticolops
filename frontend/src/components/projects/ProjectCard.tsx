import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { 
  Users, 
  GitBranch, 
  Calendar, 
  Settings, 
  ExternalLink,
  MoreVertical,
  Edit,
  Trash2,
  UserPlus
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';

export interface Project {
  id: string;
  name: string;
  description: string;
  ownerId: string;
  ownerName: string;
  memberCount: number;
  repositoryCount: number;
  lastActivity: Date;
  createdAt: Date;
  status: 'active' | 'archived' | 'draft';
  visibility: 'public' | 'private';
}

interface ProjectCardProps {
  project: Project;
  onEdit?: (project: Project) => void;
  onDelete?: (project: Project) => void;
  onInviteMembers?: (project: Project) => void;
  onViewProject?: (project: Project) => void;
  showActions?: boolean;
  isOwner?: boolean;
}

const getStatusColor = (status: Project['status']) => {
  switch (status) {
    case 'active':
      return 'bg-green-100 text-green-800';
    case 'archived':
      return 'bg-gray-100 text-gray-800';
    case 'draft':
      return 'bg-yellow-100 text-yellow-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

const getStatusText = (status: Project['status']) => {
  switch (status) {
    case 'active':
      return 'Active';
    case 'archived':
      return 'Archived';
    case 'draft':
      return 'Draft';
    default:
      return 'Unknown';
  }
};

export const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  onEdit,
  onDelete,
  onInviteMembers,
  onViewProject,
  showActions = true,
  isOwner = false,
}) => {
  const [showMenu, setShowMenu] = React.useState(false);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg font-semibold text-foreground">
              {project.name}
            </CardTitle>
            <div className="flex items-center space-x-2 mt-1">
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(project.status)}`}>
                {getStatusText(project.status)}
              </span>
              <span className="text-xs text-muted-foreground">
                {project.visibility === 'private' ? '🔒 Private' : '🌐 Public'}
              </span>
            </div>
          </div>
          
          {showActions && (
            <div className="relative">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowMenu(!showMenu)}
                className="h-8 w-8 p-0"
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
              
              {showMenu && (
                <div className="absolute right-0 top-10 bg-white border rounded-md shadow-lg z-10 min-w-[160px]">
                  <div className="py-1">
                    <button
                      onClick={() => {
                        onViewProject?.(project);
                        setShowMenu(false);
                      }}
                      className="flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full text-left"
                    >
                      <ExternalLink className="h-4 w-4" />
                      <span>View Project</span>
                    </button>
                    
                    {isOwner && (
                      <>
                        <button
                          onClick={() => {
                            onEdit?.(project);
                            setShowMenu(false);
                          }}
                          className="flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full text-left"
                        >
                          <Edit className="h-4 w-4" />
                          <span>Edit Project</span>
                        </button>
                        
                        <button
                          onClick={() => {
                            onInviteMembers?.(project);
                            setShowMenu(false);
                          }}
                          className="flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full text-left"
                        >
                          <UserPlus className="h-4 w-4" />
                          <span>Invite Members</span>
                        </button>
                        
                        <hr className="my-1" />
                        
                        <button
                          onClick={() => {
                            onDelete?.(project);
                            setShowMenu(false);
                          }}
                          className="flex items-center space-x-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 w-full text-left"
                        >
                          <Trash2 className="h-4 w-4" />
                          <span>Delete Project</span>
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </CardHeader>
      
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
          {project.description || 'No description provided'}
        </p>
        
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            <Users className="h-4 w-4" />
            <span>{project.memberCount} members</span>
          </div>
          
          <div className="flex items-center space-x-2 text-sm text-muted-foreground">
            <GitBranch className="h-4 w-4" />
            <span>{project.repositoryCount} repositories</span>
          </div>
        </div>
        
        <div className="space-y-2 text-xs text-muted-foreground">
          <div className="flex items-center space-x-2">
            <Calendar className="h-3 w-3" />
            <span>Created {formatDistanceToNow(new Date(project.createdAt), { addSuffix: true })}</span>
          </div>
          
          <div className="flex items-center space-x-2">
            <Settings className="h-3 w-3" />
            <span>Last activity {formatDistanceToNow(new Date(project.lastActivity), { addSuffix: true })}</span>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className="text-xs">Owner: {project.ownerName}</span>
          </div>
        </div>
        
        <div className="mt-4 pt-4 border-t">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onViewProject?.(project)}
            className="w-full"
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            Open Project
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};