import { ApiError } from "@/lib/api";

type ApiDetailObject = {
  code?: unknown;
  message?: unknown;
  detail?: unknown;
};

/** User-facing text for caught API / network / unknown errors. */
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const body = error.body;
    if (body && typeof body === "object" && "detail" in body) {
      const rawDetail = (body as { detail?: unknown }).detail;
      if (rawDetail && typeof rawDetail === "object") {
        const d = rawDetail as ApiDetailObject;
        if (typeof d.message === "string" && d.message.trim().length > 0) {
          return d.message;
        }
        if (typeof d.detail === "string" && d.detail.trim().length > 0) {
          return d.detail;
        }
      }
    }
    return error.message || `Request failed (${error.status})`;
  }
  if (error instanceof Error) {
    return error.message || "Something went wrong";
  }
  if (typeof error === "string") {
    return error;
  }
  return "Something went wrong. Please try again.";
}
