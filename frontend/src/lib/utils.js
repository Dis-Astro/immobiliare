import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount, currency = 'EUR') {
  return new Intl.NumberFormat('it-IT', {
    style: 'currency',
    currency: currency,
  }).format(amount);
}

export function formatDate(date, options = {}) {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('it-IT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    ...options,
  });
}

export function formatDateTime(date) {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleString('it-IT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function getStatusColor(status) {
  const colors = {
    rosso: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200' },
    giallo: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200' },
    verde: { bg: 'bg-emerald-100', text: 'text-emerald-700', border: 'border-emerald-200' },
    grigio: { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-200' },
  };
  return colors[status] || colors.grigio;
}

export function truncate(str, length = 50) {
  if (!str) return '';
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}
