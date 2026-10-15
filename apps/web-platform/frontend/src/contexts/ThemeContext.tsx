import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

type Theme = 'light' | 'dark' | 'system';

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  effectiveTheme: 'light' | 'dark';
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

function readSavedTheme(): Theme {
  if (typeof window === 'undefined') return 'system';

  try {
    const saved = window.localStorage.getItem('theme');
    return saved === 'light' || saved === 'dark' || saved === 'system' ? saved : 'system';
  } catch {
    return 'system';
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(readSavedTheme);
  const [effectiveTheme, setEffectiveTheme] = useState<'light' | 'dark'>('light');

  const setTheme = useCallback((nextTheme: Theme) => {
    setThemeState(nextTheme);
    try {
      window.localStorage.setItem('theme', nextTheme);
    } catch {
      // Theme still changes for this session when storage is unavailable.
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const root = window.document.documentElement;
    const media = window.matchMedia('(prefers-color-scheme: dark)');

    const applyTheme = () => {
      const effective: 'light' | 'dark' =
        theme === 'system' ? (media.matches ? 'dark' : 'light') : theme;
      root.classList.remove('light', 'dark');
      root.classList.add(effective);
      setEffectiveTheme(effective);
    };

    applyTheme();
    if (theme === 'system') media.addEventListener('change', applyTheme);

    return () => {
      if (theme === 'system') media.removeEventListener('change', applyTheme);
    };
  }, [theme]);

  const value = useMemo(
    () => ({ theme, setTheme, effectiveTheme }),
    [theme, setTheme, effectiveTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
