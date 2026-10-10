import { Outlet, useNavigate, useLocation } from 'react-router';
import { Activity, Cloud, FolderKanban, LayoutDashboard, LogOut, ShieldCheck, Sparkles, Search, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupContent, SidebarGroupLabel, SidebarHeader, SidebarInset, SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { getStoredUser, signOut } from '@/lib/supabaseAuth';
import { isLocalAuthEnabled, signOutLocal } from '@/lib/localAuth';

const baseMenuItems = [
  { title: 'Overview', description: 'Your workspace', url: '/admin/dashboard', icon: LayoutDashboard },
  { title: 'Documents', description: 'Files and folders', url: '/admin/cloud-documents', icon: Cloud },
  { title: 'Activity', description: 'Security and history', url: '/admin/activity', icon: Activity },
];
const localMenuItem = { title: 'Safe Workspace', description: 'On-device tools', url: '/admin/workspace', icon: FolderKanban };

export default function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = getStoredUser();
  const localMode = isLocalAuthEnabled();
  const menuItems = localMode ? [localMenuItem] : import.meta.env.PROD ? baseMenuItems : [...baseMenuItems, localMenuItem];
  const activeItem = menuItems.find(item => location.pathname === item.url || location.pathname.startsWith(`${item.url}/`));
  const handleLogout = async () => { if (localMode) await signOutLocal(); else await signOut(); navigate('/login', { replace: true }); };
  const displayName = user?.email || user?.username || 'Doka user';
  const initials = displayName.split('@')[0].slice(0, 2).toUpperCase();

  return (
    <SidebarProvider className="doka-shell min-h-svh w-full">
      <Sidebar collapsible="icon" className="doka-sidebar">
        <SidebarHeader className="px-4 pb-5 pt-5 group-data-[collapsible=icon]:px-2">
          <button type="button" onClick={() => navigate(localMode ? '/admin/workspace' : '/admin/dashboard')} className="flex items-center gap-3 rounded-xl text-left outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 group-data-[collapsible=icon]:justify-center">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[14px] bg-gradient-to-br from-cyan-300 to-blue-500 text-slate-950 shadow-lg shadow-blue-950/30"><span className="text-lg font-black">D</span></span>
            <span className="min-w-0 group-data-[collapsible=icon]:hidden"><span className="block text-[17px] font-semibold tracking-tight text-white">Doka</span><span className="mt-0.5 block text-[10px] font-semibold uppercase tracking-[.19em] text-slate-500">Document intelligence</span></span>
          </button>
          <div className="mt-5 rounded-2xl border border-white/[.08] bg-white/[.045] p-3.5 group-data-[collapsible=icon]:hidden">
            <div className="flex items-center gap-2 text-xs font-semibold text-cyan-200"><ShieldCheck className="h-4 w-4" /> Private workspace</div>
            <p className="mt-1.5 text-[11px] leading-[1.65] text-slate-400">Your documents stay scoped to your signed-in account.</p>
            <div className="mt-3 flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400"/><span className="text-[10px] font-medium text-slate-400">{localMode ? 'LOCAL SESSION' : 'CLOUD SESSION'}</span></div>
          </div>
        </SidebarHeader>
        <SidebarContent className="px-3 group-data-[collapsible=icon]:px-1">
          <SidebarGroup className="p-1">
            <SidebarGroupLabel className="px-3 pb-2 text-[10px] font-bold uppercase tracking-[.18em] text-slate-600 group-data-[collapsible=icon]:hidden">Workspace</SidebarGroupLabel>
            <SidebarGroupContent><SidebarMenu className="gap-1.5">{menuItems.map(item => <SidebarMenuItem key={item.url}>
              <SidebarMenuButton asChild tooltip={item.title} isActive={location.pathname === item.url || location.pathname.startsWith(`${item.url}/`)} className="h-[46px] rounded-xl px-3 group-data-[collapsible=icon]:justify-center">
                <button type="button" onClick={() => navigate(item.url)} aria-current={location.pathname === item.url ? 'page' : undefined}><item.icon className="h-[18px] w-[18px] shrink-0"/><span className="min-w-0 group-data-[collapsible=icon]:hidden"><span className="block text-[13px] font-semibold">{item.title}</span><span className="mt-0.5 block text-[10px] font-normal opacity-60">{item.description}</span></span></button>
              </SidebarMenuButton>
            </SidebarMenuItem>)}</SidebarMenu></SidebarGroupContent>
          </SidebarGroup>
          {import.meta.env.PROD && <div className="mx-2 mt-5 rounded-2xl border border-indigo-300/10 bg-indigo-300/[.055] p-3.5 group-data-[collapsible=icon]:hidden"><div className="flex items-center gap-2 text-xs font-semibold text-indigo-200"><Sparkles className="h-4 w-4"/> On-device tools</div><p className="mt-1.5 text-[11px] leading-[1.65] text-slate-400">OCR and Safe Workspace run locally, not in the cloud dashboard.</p></div>}
        </SidebarContent>
        <SidebarFooter className="p-3 group-data-[collapsible=icon]:px-1"><Separator className="mb-3 bg-white/[.08]"/><div className="flex min-w-0 items-center gap-2.5 group-data-[collapsible=icon]:justify-center">
          <Avatar className="h-9 w-9 shrink-0 border border-white/10"><AvatarFallback className="bg-cyan-300/15 text-xs font-bold text-cyan-100">{initials}</AvatarFallback></Avatar>
          <div className="min-w-0 flex-1 group-data-[collapsible=icon]:hidden"><p className="truncate text-xs font-semibold text-slate-100">{displayName}</p><p className="mt-0.5 text-[10px] text-slate-500">{localMode ? 'Local account' : 'Verified session'}</p></div>
          <Button variant="ghost" size="icon" onClick={handleLogout} className="h-8 w-8 shrink-0 rounded-lg text-slate-400 hover:bg-white/10 hover:text-white group-data-[collapsible=icon]:hidden" aria-label="Log out"><LogOut className="h-4 w-4"/></Button>
          <Button variant="ghost" size="icon" onClick={handleLogout} className="hidden h-8 w-8 rounded-lg text-slate-400 hover:bg-white/10 hover:text-white group-data-[collapsible=icon]:inline-flex" aria-label="Log out"><LogOut className="h-4 w-4"/></Button>
        </div></SidebarFooter>
      </Sidebar>
      <SidebarInset className="min-w-0 overflow-x-hidden bg-transparent">
        <header className="doka-topbar sticky top-0 z-20 flex min-h-[70px] w-full items-center justify-between gap-3 px-4 sm:px-7">
          <div className="flex min-w-0 items-center gap-3"><SidebarTrigger className="h-9 w-9 shrink-0 rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"/><div className="min-w-0"><div className="flex items-center gap-2"><span className="truncate text-sm font-bold tracking-tight text-slate-900 dark:text-slate-100">{activeItem?.title || 'Workspace'}</span><ChevronRight className="hidden h-3.5 w-3.5 text-slate-400 sm:block"/><Badge variant="outline" className="hidden rounded-full border-emerald-200 bg-emerald-50 px-2 py-0 text-[9px] font-bold tracking-wide text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300 sm:inline-flex">{localMode ? 'LOCAL' : 'CLOUD'}</Badge></div><p className="mt-0.5 hidden text-[11px] text-slate-500 sm:block">{activeItem?.description || 'Your secure document workspace'}</p></div></div>
          <div className="flex shrink-0 items-center gap-2"><div className="hidden h-9 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs text-slate-400 dark:border-slate-800 dark:bg-slate-900 md:flex"><Search className="h-3.5 w-3.5"/><span>Secure workspace</span><kbd className="ml-4 rounded border border-slate-200 px-1.5 py-0.5 text-[9px] dark:border-slate-700">DOKA</kbd></div><span className="hidden h-9 items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 text-[11px] font-semibold text-emerald-700 dark:border-emerald-900/70 dark:bg-emerald-950/30 dark:text-emerald-300 sm:inline-flex"><ShieldCheck className="h-3.5 w-3.5"/> Private workspace</span><ThemeToggle/></div>
        </header>
        <main className="mx-auto w-full max-w-[1500px] p-4 sm:p-6 lg:p-8"><Outlet/></main>
      </SidebarInset>
    </SidebarProvider>
  );
}
