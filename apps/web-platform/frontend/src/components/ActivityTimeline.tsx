import { Clock, Upload, Download, Eye, Edit, Trash2, User } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';

export interface ActivityEvent {
  id: string;
  type: 'upload' | 'download' | 'view' | 'edit' | 'delete' | 'share';
  documentName: string;
  user: string;
  timestamp: Date;
  details?: string;
}

const activityIcons = {
  upload: Upload,
  download: Download,
  view: Eye,
  edit: Edit,
  delete: Trash2,
  share: User,
};

const activityColors = {
  upload: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400',
  download: 'bg-blue-100 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400',
  view: 'bg-purple-100 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400',
  edit: 'bg-amber-100 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400',
  delete: 'bg-red-100 text-red-600 dark:bg-red-900/20 dark:text-red-400',
  share: 'bg-pink-100 text-pink-600 dark:bg-pink-900/20 dark:text-pink-400',
};

interface ActivityTimelineProps {
  activities: ActivityEvent[];
  maxItems?: number;
}

export default function ActivityTimeline({ activities, maxItems = 10 }: ActivityTimelineProps) {
  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000 / 60);
    
    if (diff < 1) return 'Just now';
    if (diff < 60) return `${diff}m ago`;
    if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
    if (diff < 10080) return `${Math.floor(diff / 1440)}d ago`;
    return date.toLocaleDateString();
  };

  const displayedActivities = activities.slice(0, maxItems);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="w-5 h-5" />
          Activity Timeline
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {displayedActivities.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-8">
              No recent activity
            </p>
          ) : (
            displayedActivities.map((activity, index) => {
              const Icon = activityIcons[activity.type];
              return (
                <div key={activity.id} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className={cn(
                      'w-10 h-10 rounded-full flex items-center justify-center',
                      activityColors[activity.type]
                    )}>
                      <Icon className="w-5 h-5" />
                    </div>
                    {index < displayedActivities.length - 1 && (
                      <div className="w-0.5 flex-1 bg-slate-200 dark:bg-slate-700 mt-2" />
                    )}
                  </div>
                  <div className="flex-1 pb-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                          {activity.type.charAt(0).toUpperCase() + activity.type.slice(1)} - {activity.documentName}
                        </p>
                        {activity.details && (
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                            {activity.details}
                          </p>
                        )}
                        <div className="flex items-center gap-2 mt-2">
                          <Avatar className="w-5 h-5">
                            <AvatarFallback className="text-xs bg-slate-200 dark:bg-slate-700">
                              {activity.user.substring(0, 2).toUpperCase()}
                            </AvatarFallback>
                          </Avatar>
                          <p className="text-xs text-slate-500 dark:text-slate-400">
                            {activity.user}
                          </p>
                          <span className="text-slate-300 dark:text-slate-600">•</span>
                          <p className="text-xs text-slate-500 dark:text-slate-400">
                            {formatTime(activity.timestamp)}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function generateMockActivities(): ActivityEvent[] {
  const now = new Date();
  return [
    {
      id: '1',
      type: 'upload',
      documentName: 'invoice_001.pdf',
      user: 'John Doe',
      timestamp: new Date(now.getTime() - 1000 * 60 * 5),
      details: 'Uploaded via drag and drop',
    },
    {
      id: '2',
      type: 'view',
      documentName: 'contract_2024.pdf',
      user: 'Jane Smith',
      timestamp: new Date(now.getTime() - 1000 * 60 * 15),
    },
    {
      id: '3',
      type: 'download',
      documentName: 'report_q3.xlsx',
      user: 'Bob Johnson',
      timestamp: new Date(now.getTime() - 1000 * 60 * 30),
    },
    {
      id: '4',
      type: 'edit',
      documentName: 'meeting_notes.docx',
      user: 'Alice Williams',
      timestamp: new Date(now.getTime() - 1000 * 60 * 45),
      details: 'Updated content',
    },
    {
      id: '5',
      type: 'share',
      documentName: 'presentation.pptx',
      user: 'John Doe',
      timestamp: new Date(now.getTime() - 1000 * 60 * 60),
      details: 'Shared with team',
    },
    {
      id: '6',
      type: 'delete',
      documentName: 'old_document.pdf',
      user: 'Admin',
      timestamp: new Date(now.getTime() - 1000 * 60 * 120),
    },
  ];
}
