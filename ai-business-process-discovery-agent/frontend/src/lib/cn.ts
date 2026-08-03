/** Minimal class-name joiner. Avoids a dependency for a six-line utility. */
export function cn(...values: (string | false | null | undefined)[]): string {
  return values.filter(Boolean).join(' ')
}
