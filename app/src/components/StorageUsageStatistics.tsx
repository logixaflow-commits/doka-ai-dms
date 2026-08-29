import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { HardDrive, FileText, Image, File, AlertTriangle } from 'lucide-react';

interface StorageCategory {
  name: string;
  used: number;
  total: number;
  icon: React.ReactNode;
  color: string;
}

interface StorageUsageStatisticsProps {
  totalUsed: number;
  totalCapacity: number;
  categories: StorageCategory[];
}

export default function StorageUsageStatistics({ 
  totalUsed, 
  totalCapacity, 
  categories 
}: StorageUsageStatisticsProps) {
  const usagePercentage = (totalUsed / totalCapacity) * 100;
  const remaining = totalCapacity - totalUsed;

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const isNearCapacity = usagePercentage > 85;

  return (
    <div className="space-y-6">
      {/* Overall Storage */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <HardDrive className="w-5 h-5" />
            Overall Storage Usage
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                {formatBytes(totalUsed)}
              </p>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                of {formatBytes(totalCapacity)} used
              </p>
            </div>
            <div className={`text-right ${isNearCapacity ? 'text-amber-600' : 'text-slate-600 dark:text-slate-400'}`}>
              <p className="text-2xl font-bold">{usagePercentage.toFixed(1)}%</p>
              <p className="text-sm">{formatBytes(remaining)} remaining</p>
            </div>
          </div>

          <Progress 
            value={usagePercentage} 
            className={isNearCapacity ? 'h-3' : 'h-2'}
          />

          {isNearCapacity && (
            <div className="flex items-center gap-2 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
              <p className="text-sm text-amber-800 dark:text-amber-300">
                Storage is nearly full. Consider upgrading or cleaning up old files.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Storage by Category */}
      <div className="grid gap-4 md:grid-cols-2">
        {categories.map((category) => {
          const categoryPercentage = (category.used / category.total) * 100;
          return (
            <Card key={category.name}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className={`p-2 rounded-lg ${category.color}`}>
                      {category.icon}
                    </div>
                    <CardTitle className="text-base">{category.name}</CardTitle>
                  </div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    {categoryPercentage.toFixed(1)}%
                  </p>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                <Progress value={categoryPercentage} className="h-2" />
                <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
                  <span>{formatBytes(category.used)} used</span>
                  <span>{formatBytes(category.total)} total</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Storage Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle>Storage Recommendations</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 mt-0.5">•</span>
              <span>Compress large PDF files to save space</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 mt-0.5">•</span>
              <span>Delete duplicate or outdated documents</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 mt-0.5">•</span>
              <span>Archive old documents to external storage</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-500 mt-0.5">•</span>
              <span>Consider upgrading storage plan if needed</span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

export function generateMockStorageData(): StorageUsageStatisticsProps {
  return {
    totalUsed: 45.5 * 1024 * 1024 * 1024, // 45.5 GB
    totalCapacity: 100 * 1024 * 1024 * 1024, // 100 GB
    categories: [
      {
        name: 'PDFs',
        used: 15.5 * 1024 * 1024 * 1024,
        total: 20 * 1024 * 1024 * 1024,
        icon: <FileText className="w-4 h-4" />,
        color: 'bg-red-100 text-red-600 dark:bg-red-900/20 dark:text-red-400',
      },
      {
        name: 'Images',
        used: 8.2 * 1024 * 1024 * 1024,
        total: 15 * 1024 * 1024 * 1024,
        icon: <Image className="w-4 h-4" />,
        color: 'bg-blue-100 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400',
      },
      {
        name: 'Documents',
        used: 12.3 * 1024 * 1024 * 1024,
        total: 25 * 1024 * 1024 * 1024,
        icon: <File className="w-4 h-4" />,
        color: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400',
      },
      {
        name: 'Other',
        used: 9.5 * 1024 * 1024 * 1024,
        total: 40 * 1024 * 1024 * 1024,
        icon: <HardDrive className="w-4 h-4" />,
        color: 'bg-purple-100 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400',
      },
    ],
  };
}
