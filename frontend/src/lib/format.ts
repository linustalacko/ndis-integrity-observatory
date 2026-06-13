// Shared money formatter — compact, tabular-friendly.
export function money(n: number | null | undefined): string {
	if (n === null || n === undefined) return '—';
	if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
	if (n >= 1e6) return `$${(n / 1e6).toFixed(n >= 1e7 ? 1 : 2)}M`;
	if (n >= 1e3) return `$${n >= 1e4 ? Math.round(n / 1e3) : (n / 1e3).toFixed(1)}k`;
	return `$${Math.round(n)}`;
}
