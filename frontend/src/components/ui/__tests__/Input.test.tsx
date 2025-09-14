import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Input } from '../Input';

describe('Input', () => {
  it('renders with label', () => {
    render(<Input label="Email" />);
    const label = screen.getByText('Email');
    const input = screen.getByLabelText('Email');
    
    expect(label).toBeInTheDocument();
    expect(input).toBeInTheDocument();
  });

  it('renders without label', () => {
    render(<Input placeholder="Enter text" />);
    const input = screen.getByPlaceholderText('Enter text');
    expect(input).toBeInTheDocument();
  });

  it('displays error message', () => {
    render(<Input label="Email" error="Invalid email" />);
    const errorMessage = screen.getByText('Invalid email');
    const input = screen.getByLabelText('Email');
    
    expect(errorMessage).toBeInTheDocument();
    expect(input).toHaveClass('border-destructive');
  });

  it('handles value changes', () => {
    const handleChange = vi.fn();
    render(<Input label="Email" onChange={handleChange} />);
    
    const input = screen.getByLabelText('Email');
    fireEvent.change(input, { target: { value: 'test@example.com' } });
    
    expect(handleChange).toHaveBeenCalledTimes(1);
  });

  it('can be required', () => {
    render(<Input label="Email" required />);
    const input = screen.getByLabelText('Email');
    expect(input).toBeRequired();
  });
});