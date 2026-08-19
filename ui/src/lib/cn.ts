// Merges Tailwind class strings with correct override semantics — plain
// string concatenation doesn't guarantee a later class wins (that depends on
// generation order in the compiled stylesheet, not string position), so any
// component that appends a caller-supplied className to its own base classes
// must go through this, not a template literal.

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
