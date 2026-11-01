/** Same-origin owner transport. Credentials stay in memory; mutations never retry. */
export class ApiError extends Error {
  constructor(public status: number, public reason: string, message: string) { super(message); }
}

export class OwnerApi {
  csrf = '';
  constructor(private expired: () => void) {}

  async request<T>(path: string, body?: unknown, ownerKey?: string): Promise<T> {
    const startedWith = this.csrf;
    const headers: Record<string, string> = {};
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
      if (!ownerKey) headers['X-CSRF-Token'] = this.csrf;
    }
    if (ownerKey) headers.Authorization = `Bearer ${ownerKey}`;
    let response: Response;
    try {
      response = await fetch(path, { method: body === undefined ? 'GET' : 'POST',
        credentials: 'same-origin', cache: 'no-store', headers,
        ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    } catch {
      throw new ApiError(0, 'connection', 'Could not connect. Check the local server, then try again deliberately.');
    }
    let value;
    try { value = await response.json(); }
    catch { throw new ApiError(response.status, 'invalid_response', 'The server returned an unreadable response. Inspect status before retrying.'); }
    if (!response.ok) {
      if (response.status === 401 && !ownerKey && startedWith === this.csrf) { this.csrf = ''; this.expired(); }
      throw new ApiError(response.status, value.reason ?? 'request_failed',
        value.message ?? 'The request was not accepted. Refresh status before trying again.');
    }
    if (body !== undefined && !ownerKey && startedWith !== this.csrf) {
      throw new ApiError(409, 'session_changed', 'Session changed while the request was in progress. Refresh status; no action was replayed.');
    }
    return value as T;
  }
}
