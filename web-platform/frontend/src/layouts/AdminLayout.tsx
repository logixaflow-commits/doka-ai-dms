import { Outlet, useNavigate, useLocation } from 'react-router';
import { Cloud, FolderKanban, LayoutDashboard, LogOut, ShieldCheck, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ThemeToggle } from '@/components/ThemeToggle';
import {
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupContent,
  SidebarGroupLabel, SidebarHeader, SidebarMenu, SidebarMenuButton,
  SidebarMenuItem, SidebarProvider, SidebarTrigger,
} from '@/components/ui/sidebar';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { getStoredUser, signOut } from '@/lib/supabaseAuth';

const baseMenuItems = [
  { title: 'Overview', url: '/admin/dashboard', icon: LayoutDashboard },
  { title: 'Cloud documents', url: '/admin/cloud-documents', icon: Cloud },
];

const localMenuItem = { title: 'Safe Workspace', url: '/admin/workspace', icon: FolderKanban };

export default function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = getStoredUser();
  const menuItems = import.meta.env.PROD ? baseMenuItems : [...baseMenuItems, localMenuItem];

  const handleLogout = async () => {
    await signOut();
    navigate('/login', { replace: true });
  };

  const displayName = user?.email || 'Doka user';
  const initials = displayName.split('@')[0].slice(0, 2).toUpperCase();
  const pageTitle = menuItems.find(item => item.url === location.pathname)?.title || 'Doka';

  return (
    <SidebarProvider>
      <div className="doka-shell flex min-h-screen w-full bg-[#f5f7fb] dark:bg-slate-950">
        <Sidebar className="border-r border-slate-800/70 bg-[#101b31] text-slate-100 [&_[data-sidebar=sidebar]]:bg-[#101b31] [&_[data-sidebar=sidebar]]:text-slate-100">
          <SidebarHeader className="px-5 pb-5 pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-300 to-blue-500 text-slate-950 shadow-lg shadow-blue-950/30">
                <span className="text-lg font-black tracking-tight">D</span>
              </div>
              <div className="min-w-0">
                <p className="text-lg font-semibold tracking-tight text-white">Doka</p>
                <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-slate-400">Document workspace</p>
              </div>
            </div>
            <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.06] p-3">
              <div className="flex items-center gap-2 text-xs font-medium text-cyan-200"><ShieldCheck className="h-4 w-4" /> Private cloud space</div>
              <p className="mt-1.5 text-xs leading-5 text-slate-400">Your files are isolated to your signed-in account.</p>
            </div>
          </SidebarHeader>
          <SidebarContent className="px-3">
            <SidebarGroup>
              <SidebarGroupLabel className="px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">Workspace</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu className="gap-1.5">
                  {menuItems.map(item => (
                    <SidebarMenuItem key={item.url}>
                      <SidebarMenuButton
                        asChild
                        isActive={location.pathname === item.url}
                        onClick={() => navigate(item.url)}
                        className="h-11 rounded-xl px-3 text-slate-300 hover:bg-white/10 hover:text-white data-[active=true]:bg-cyan-300/15 data-[active=true]:font-semibold data-[active=true]:text-cyan-200"
                      >
                        <button className="w-full"><item.icon className="h-[18px] w-[18px]" /><span>{item.title}</span></button>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
            {import.meta.env.PROD && <div className="mx-3 mt-5 rounded-2xl border border-white/10 bg-white/[0.04] p-3">
              <div className="flex items-center gap-2 text-xs font-medium text-slate-200"><Sparkles className="h-4 w-4 text-violet-300" /> Local tools</div>
              <p className="mt-1.5 text-xs leading-5 text-slate-400">OCR and Safe Workspace run on your computer, not in this cloud dashboard.</p>
            </div>}
          </SidebarContent>
          <SidebarFooter className="p-4">
            <Separator className="mb-4 bg-white/10" />
            <div className="flex items-center gap-2">
              <Avatar className="h-9 w-9 border border-white/10"><AvatarFallback className="bg-cyan-300/15 text-xs font-semibold text-cyan-100">{initials}</AvatarFallback></Avatar>
              <div className="min-w-0 flex-1"><p className="truncate text-xs font-medium text-slate-100">{displayName}</p><p className="text-[10px] text-slate-400">Signed in with Supabase</p></div>
              <Button variant="ghost" size="icon" onClick={handleLogout} className="h-8 w-8 rounded-lg text-slate-400 hover:bg-white/10 hover:text-white" aria-label="Log out"><LogOut className="h-4 w-4" /></Button>
            </div>
          </SidebarFooter>
        </Sidebar>

        <main className="min-w-0 flex-1 overflow-x-hidden">
          <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-slate-200/80 bg-white/85 px-4 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/85 sm:px-7">
            <div className="flex min-w-0 items-center gap-3">
              <SidebarTrigger className="rounded-xl" />
              <div className="min-w-0"><div className="flex items-center gap-2"><p className="truncate text-sm font-semibold text-slate-900 dark:text-white">{pageTitle}</p><Badge variant="outline" className="hidden rounded-full border-emerald-200 bg-emerald-50 text-[10px] font-medium text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300 sm:inline-flex">CLOUD</Badge></div><p className="hidden text-xs text-slate-500 sm:block">Your secure document workspace</p></div>
            </div>
            <div className="flex items-center gap-2"><span className="hidden items-center gap-1.5 text-xs text-slate-500 md:inline-flex"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Account protected</span><ThemeToggle /></div>
          </header>
          <div className="mx-auto w-full max-w-[1440px] p-4 sm:p-6 lg:p-8"><Outlet /></div>
        </main>
      </div>
    </SidebarProvider>
  );
}
