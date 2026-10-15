import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';

const COLORS = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

interface DocumentTypeData {
  name: string;
  count: number;
}

interface ActivityData {
  date: string;
  uploads: number;
  downloads: number;
  views: number;
}

interface StorageData {
  name: string;
  used: number;
  total: number;
}

export function DocumentTypeChart({ data }: { data: DocumentTypeData[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Documents by Type</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              outerRadius={80}
              fill="#8884d8"
              dataKey="count"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function ActivityChart({ data }: { data: ActivityData[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Document Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="uploads" stroke="#2563eb" strokeWidth={2} />
            <Line type="monotone" dataKey="downloads" stroke="#10b981" strokeWidth={2} />
            <Line type="monotone" dataKey="views" stroke="#f59e0b" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function StorageUsageChart({ data }: { data: StorageData[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Storage Usage</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="used" fill="#2563eb" name="Used (GB)" />
            <Bar dataKey="total" fill="#e2e8f0" name="Total (GB)" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function ProcessingTimeChart({ data }: { data: { name: string; time: number }[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Average Processing Time</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} layout="horizontal">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis dataKey="name" type="category" width={100} />
            <Tooltip />
            <Bar dataKey="time" fill="#8b5cf6" name="Time (seconds)" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// Mock data generators
export const generateDocumentTypeData = (): DocumentTypeData[] => [
  { name: 'PDF', count: 45 },
  { name: 'Word', count: 30 },
  { name: 'Excel', count: 20 },
  { name: 'Images', count: 15 },
  { name: 'Other', count: 10 },
];

export const generateActivityData = (): ActivityData[] => [
  { date: 'Mon', uploads: 12, downloads: 8, views: 45 },
  { date: 'Tue', uploads: 15, downloads: 12, views: 52 },
  { date: 'Wed', uploads: 8, downloads: 15, views: 38 },
  { date: 'Thu', uploads: 20, downloads: 18, views: 65 },
  { date: 'Fri', uploads: 25, downloads: 22, views: 78 },
  { date: 'Sat', uploads: 10, downloads: 8, views: 32 },
  { date: 'Sun', uploads: 5, downloads: 6, views: 25 },
];

export const generateStorageData = (): StorageData[] => [
  { name: 'PDFs', used: 15.5, total: 20 },
  { name: 'Images', used: 8.2, total: 15 },
  { name: 'Documents', used: 12.3, total: 25 },
  { name: 'Other', used: 4.1, total: 10 },
];

export const generateProcessingTimeData = () => [
  { name: 'PDF', time: 3.5 },
  { name: 'Word', time: 2.1 },
  { name: 'Excel', time: 1.8 },
  { name: 'Images', time: 4.2 },
  { name: 'Other', time: 2.5 },
];
