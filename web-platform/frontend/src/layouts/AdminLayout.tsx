import { Outlet, useNavigate, useLocation } from 'react-router';
import { LayoutDashboard, LogOut, FolderKanban } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupContent, SidebarGroupLabel, SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';

const menuItems = [
  { title: 'Dashboard', url: '/admin/dashboard', icon: LayoutDashboard },
  { title: 'Safe Workspace', url: '/admin/workspace', icon: FolderKanban },
];

export default function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('username');
    navigate('/login');
  };
  const username = localStorage.getItem('username') || 'Admin';

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-slate-50 dark:bg-slate-900">
        <Sidebar>
          <SidebarHeader className="p-4">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600"><span className="text-sm font-bold text-white">DMS</span></div>
              <div><h1 className="font-semibold text-slate-900 dark:text-slate-100">Personal Local DMS</h1><p className="text-xs text-slate-500 dark:text-slate-400">Safe Workspace</p></div>
            </div>
          </SidebarHeader>
          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupLabel>Main Menu</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {menuItems.map((item) => (
                    <SidebarMenuItem key={item.url}>
                      <SidebarMenuButton asChild isActive={location.pathname === item.url} onClick={() => navigate(item.url)}>
                        <button className="w-full flex items-center gap-2"><item.icon className="h-4 w-4" /><span>{item.title}</span></button>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>
          <SidebarFooter className="p-4">
            <Separator className="mb-4" />
            <div className="flex items-center justify-between gap-2">
              <div className="flex min-w-0 items-center gap-2">
                <Avatar className="h-8 w-8"><AvatarFallback className="bg-blue-100 text-xs text-blue-600">{username.substring(0, 2).toUpperCase()}</AvatarFallback></Avatar>
                <div className="min-w-0"><span className="block truncate text-sm font-medium text-slate-900 dark:text-slate-100">{username}</span><span className="text-xs text-slate-500 dark:text-slate-400">Local admin</span></div>
              </div>
              <div className="flex gap-1"><ThemeToggle /><Button variant="ghost" size="icon" onClick={handleLogout} className="h-8 w-8"><LogOut className="h-4 w-4" /></Button></div>
            </div>
          </SidebarFooter>
        </Sidebar>
        <main className="flex-1 overflow-auto">
          <div className="p-6">
            <div className="mb-6 flex items-center gap-4"><SidebarTrigger /><div><h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{menuItems.find(item => item.url === location.pathname)?.title || 'Personal Local DMS'}</h2><p className="text-xs text-slate-500">Original source remains read-only.</p></div></div>
            <Outlet />
          </div>
        </main>
      </div>
    </SidebarProvider>
  );
}
