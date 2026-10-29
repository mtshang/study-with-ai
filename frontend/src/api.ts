export type Account = { id: string; username: string; created_at: string };
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function accountRequest<T>(
  path: string,
  data?: unknown,
  signal?: AbortSignal,
  options?: { method?: string; headers?: Record<string, string>; responseType?: "blob" },
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method: options?.method || (data === undefined ? "GET" : "POST"),
      credentials: "same-origin",
      signal,
      headers: { ...(data === undefined || data instanceof FormData ? {} : { "Content-Type": "application/json" }), ...options?.headers },
      body: data === undefined ? undefined : data instanceof FormData ? data : JSON.stringify(data),
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError("暂时无法连接后端，请确认后端已启动后重试。", 0);
  }
  if (response.ok && options?.responseType === "blob") return await response.blob() as T;
  const body =
    response.status === 204 ? null : await response.json().catch(() => null);
  if(response.ok && response.status!==204 && body===null)
    throw new ApiError("服务器返回内容异常，无法确认操作结果；请核对后重试。",502);
  if (!response.ok)
    throw new ApiError(
      typeof body?.detail === "string"
        ? body.detail
        : "服务暂不可用，请稍后重试。",
      response.status,
    );
  return body as T;
}
