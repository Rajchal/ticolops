import React from 'react';
import { cn } from '../../lib/utils';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  labelClassName?: string; // NEW
  error?: string;
}

export const Input: React.FC<InputProps> = ({
  label,
  labelClassName,
  error,
  className,
  id,
  ...props
}) => {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');

  return (
    <div className="space-y-2">
      {label && (
        <label
          htmlFor={inputId}
          className={cn(
            'text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
            labelClassName // merge custom label classes
          )}
        >
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={cn('input', error && 'border-destructive', className)}
        {...props}
      />
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
};
