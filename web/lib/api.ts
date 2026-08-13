export const API_BASE =
  process.env.NEXT_PUBLIC_EV_API_BASE?.replace(/\/+$/, "") ?? "";

export function apiUrl(path: string) {
  if (!path.startsWith("/")) path = `/${path}`;
  return `${API_BASE}${path}`;
}

