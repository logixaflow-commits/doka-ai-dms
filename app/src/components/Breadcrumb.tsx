import { useLocation, Link } from 'react-router';
import { ChevronRight, Home } from 'lucide-react';
import { cn } from '@/lib/utils';

interface BreadcrumbItem {
  label: string;
  href?: string;
}

export default function Breadcrumb() {
  const location = useLocation();

  const getBreadcrumbs = (): BreadcrumbItem[] => {
    const pathnames = location.pathname.split('/').filter((x) => x);
    
    if (pathnames.length === 0) {
      return [{ label: 'Dashboard', href: '/admin/dashboard' }];
    }

    const breadcrumbs: BreadcrumbItem[] = [
      { label: 'Dashboard', href: '/admin/dashboard' },
    ];

    let currentPath = '';
    pathnames.forEach((segment, index) => {
      currentPath += `/${segment}`;
      
      // Convert path segment to readable label
      const label = segment
        .split('-')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');

      breadcrumbs.push({
        label,
        href: currentPath,
      });
    });

    return breadcrumbs;
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <nav className="flex items-center space-x-2 text-sm text-slate-600 dark:text-slate-400">
      {breadcrumbs.map((item, index) => (
        <div key={item.href} className="flex items-center">
          {index > 0 && (
            <ChevronRight className="w-4 h-4 mx-2 text-slate-400" />
          )}
          {item.href ? (
            <Link
              to={item.href}
              className={cn(
                'hover:text-slate-900 dark:hover:text-slate-100 transition-colors',
                index === breadcrumbs.length - 1
                  ? 'text-slate-900 dark:text-slate-100 font-medium'
                  : ''
              )}
            >
              {index === 0 && <Home className="w-4 h-4 inline mr-1" />}
              {item.label}
            </Link>
          ) : (
            <span className="text-slate-900 dark:text-slate-100 font-medium">
              {item.label}
            </span>
          )}
        </div>
      ))}
    </nav>
  );
}
