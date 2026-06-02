export const API_BASE =
  process.env.NEXT_PUBLIC_JARVIS_API_BASE?.replace(/\/+$/, "") ?? "";

export function apiUrl(path: string) {
  if (!path.startsWith("/")) path = `/${path}`;
  return `${API_BASE}${path}`;
}

