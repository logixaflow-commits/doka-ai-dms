import { useState, useEffect } from 'react';
import { Check, X, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ValidationRule {
  validate: (value: string) => boolean;
  message: string;
}

export interface FieldValidation {
  isValid: boolean;
  message: string;
}

export function useFieldValidation(
  value: string,
  rules: ValidationRule[],
  validateOnBlur: boolean = false
) {
  const [validation, setValidation] = useState<FieldValidation>({
    isValid: true,
    message: '',
  });
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (touched || !validateOnBlur) {
      const failedRule = rules.find((rule) => !rule.validate(value));
      setValidation({
        isValid: !failedRule,
        message: failedRule?.message || '',
      });
    }
  }, [value, rules, touched, validateOnBlur]);

  const handleBlur = () => {
    setTouched(true);
  };

  return { validation, handleBlur, touched };
}

export const validationRules = {
  required: (message: string = 'This field is required'): ValidationRule => ({
    validate: (value) => value.trim().length > 0,
    message,
  }),
  minLength: (min: number, message?: string): ValidationRule => ({
    validate: (value) => value.length >= min,
    message: message || `Must be at least ${min} characters`,
  }),
  maxLength: (max: number, message?: string): ValidationRule => ({
    validate: (value) => value.length <= max,
    message: message || `Must be no more than ${max} characters`,
  }),
  email: (message: string = 'Invalid email address'): ValidationRule => ({
    validate: (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
    message,
  }),
  password: (message?: string): ValidationRule => ({
    validate: (value) => value.length >= 8,
    message: message || 'Password must be at least 8 characters',
  }),
  match: (matchValue: string, message?: string): ValidationRule => ({
    validate: (value) => value === matchValue,
    message: message || 'Passwords do not match',
  }),
  url: (message: string = 'Invalid URL'): ValidationRule => ({
    validate: (value) => {
      if (!value) return true;
      try {
        new URL(value);
        return true;
      } catch {
        return false;
      }
    },
    message,
  }),
};

interface ValidationMessageProps {
  validation: FieldValidation;
  touched: boolean;
}

export function ValidationMessage({ validation, touched }: ValidationMessageProps) {
  if (!touched || validation.isValid) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 mt-1 text-sm text-red-600 dark:text-red-400 fade-in">
      <X className="w-4 h-4" />
      <span>{validation.message}</span>
    </div>
  );
}

interface ValidatedInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  validation: FieldValidation;
  touched: boolean;
}

export function ValidatedInput({
  validation,
  touched,
  className,
  ...props
}: ValidatedInputProps) {
  return (
    <div className="relative">
      <input
        className={cn(
          'w-full px-3 py-2 border rounded-md transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-blue-500',
          touched && !validation.isValid
            ? 'border-red-500 focus:ring-red-500'
            : 'border-slate-300 dark:border-slate-600',
          className
        )}
        onBlur={props.onBlur}
        aria-invalid={!validation.isValid && touched}
        aria-describedby={
          !validation.isValid && touched ? `${props.id}-error` : undefined
        }
        {...props}
      />
      {touched && validation.isValid && props.value && (
        <Check className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-emerald-500" />
      )}
      {touched && !validation.isValid && (
        <AlertCircle className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-red-500" />
      )}
    </div>
  );
}

interface PasswordStrengthProps {
  password: string;
}

export function PasswordStrength({ password }: PasswordStrengthProps) {
  const calculateStrength = (pwd: string): number => {
    let strength = 0;
    if (pwd.length >= 8) strength += 1;
    if (pwd.length >= 12) strength += 1;
    if (/[a-z]/.test(pwd)) strength += 1;
    if (/[A-Z]/.test(pwd)) strength += 1;
    if (/[0-9]/.test(pwd)) strength += 1;
    if (/[^a-zA-Z0-9]/.test(pwd)) strength += 1;
    return Math.min(strength, 4);
  };

  const strength = calculateStrength(password);
  const colors = [
    'bg-red-500',
    'bg-orange-500',
    'bg-amber-500',
    'bg-emerald-500',
  ];
  const labels = ['Weak', 'Fair', 'Good', 'Strong'];

  if (!password) return null;

  return (
    <div className="mt-2 space-y-2">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={cn(
              'h-1 flex-1 rounded-full transition-colors',
              i < strength ? colors[strength - 1] : 'bg-slate-200 dark:bg-slate-700'
            )}
          />
        ))}
      </div>
      <p className="text-xs text-slate-600 dark:text-slate-400">
        Password strength: <span className="font-medium">{labels[strength - 1] || 'Very weak'}</span>
      </p>
    </div>
  );
}
