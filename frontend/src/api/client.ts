export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
      body: body !== undefined ? JSON.stringify(body) : null,
    });
  } catch {
    throw new ApiError(0, 'Netzwerkfehler – Server nicht erreichbar');
  }

  if (!response.ok) {
    let message = `Fehler ${response.status}`;
    try {
      const data: unknown = await response.json();
      if (
        typeof data === 'object' &&
        data !== null &&
        'error' in data &&
        typeof (data as { error: unknown }).error === 'string'
      ) {
        message = (data as { error: string }).error;
      }
    } catch {
      // keep default message
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body: unknown) => request<T>('POST', path, body),
  put: <T>(path: string, body: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, body),
  del: <T = void>(path: string) => request<T>('DELETE', path),
};
