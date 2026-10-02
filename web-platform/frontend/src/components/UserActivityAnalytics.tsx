import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Users, TrendingUp, Activity, Eye } from 'lucide-react';

interface UserActivityData {
  userId: string;
  username: string;
  uploads: number;
  downloads: number;
  views: number;
  lastActive: Date;
}

interface UserActivityAnalyticsProps {
  data: UserActivityData[];
}

export default function UserActivityAnalytics({ data }: UserActivityAnalyticsProps) {
  const totalUploads = data.reduce((sum, user) => sum + user.uploads, 0);
  const totalDownloads = data.reduce((sum, user) => sum + user.downloads, 0);
  const totalViews = data.reduce((sum, user) => sum + user.views, 0);
  const activeUsers = data.filter(user => {
    const hoursSinceActive = (Date.now() - user.lastActive.getTime()) / (1000 * 60 * 60);
    return hoursSinceActive < 24;
  }).length;

  const formatTime = (date: Date) => {
    const hoursSinceActive = (Date.now() - date.getTime()) / (1000 * 60 * 60);
    if (hoursSinceActive < 1) return 'Active now';
    if (hoursSinceActive < 24) return `${Math.floor(hoursSinceActive)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="h-4 w-4 text-slate-600 dark:text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.length}</div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {activeUsers} active in last 24h
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Uploads</CardTitle>
            <TrendingUp className="h-4 w-4 text-emerald-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalUploads}</div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Across all users
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Downloads</CardTitle>
            <Activity className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalDownloads}</div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Across all users
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Views</CardTitle>
            <Eye className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalViews}</div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Across all users
            </p>
          </CardContent>
        </Card>
      </div>

      {/* User Activity Table */}
      <Card>
        <CardHeader>
          <CardTitle>User Activity Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  <th className="text-left p-3 text-sm font-medium text-slate-600 dark:text-slate-400">
                    User
                  </th>
                  <th className="text-left p-3 text-sm font-medium text-slate-600 dark:text-slate-400">
                    Uploads
                  </th>
                  <th className="text-left p-3 text-sm font-medium text-slate-600 dark:text-slate-400">
                    Downloads
                  </th>
                  <th className="text-left p-3 text-sm font-medium text-slate-600 dark:text-slate-400">
                    Views
                  </th>
                  <th className="text-left p-3 text-sm font-medium text-slate-600 dark:text-slate-400">
                    Last Active
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.map((user) => (
                  <tr key={user.userId} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="p-3">
                      <div className="font-medium text-slate-900 dark:text-slate-100">
                        {user.username}
                      </div>
                    </td>
                    <td className="p-3 text-slate-600 dark:text-slate-400">
                      {user.uploads}
                    </td>
                    <td className="p-3 text-slate-600 dark:text-slate-400">
                      {user.downloads}
                    </td>
                    <td className="p-3 text-slate-600 dark:text-slate-400">
                      {user.views}
                    </td>
                    <td className="p-3">
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        (Date.now() - user.lastActive.getTime()) / (1000 * 60 * 60) < 24
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-400'
                          : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                      }`}>
                        {formatTime(user.lastActive)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function generateMockUserActivityData(): UserActivityData[] {
  const now = new Date();
  return [
    {
      userId: '1',
      username: 'John Doe',
      uploads: 45,
      downloads: 32,
      views: 120,
      lastActive: new Date(now.getTime() - 1000 * 60 * 30),
    },
    {
      userId: '2',
      username: 'Jane Smith',
      uploads: 38,
      downloads: 45,
      views: 98,
      lastActive: new Date(now.getTime() - 1000 * 60 * 60 * 2),
    },
    {
      userId: '3',
      username: 'Bob Johnson',
      uploads: 22,
      downloads: 18,
      views: 65,
      lastActive: new Date(now.getTime() - 1000 * 60 * 60 * 5),
    },
    {
      userId: '4',
      username: 'Alice Williams',
      uploads: 55,
      downloads: 67,
      views: 145,
      lastActive: new Date(now.getTime() - 1000 * 60 * 15),
    },
    {
      userId: '5',
      username: 'Charlie Brown',
      uploads: 12,
      downloads: 8,
      views: 35,
      lastActive: new Date(now.getTime() - 1000 * 60 * 60 * 24),
    },
  ];
}
