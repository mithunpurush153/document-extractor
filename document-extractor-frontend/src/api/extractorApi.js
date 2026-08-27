/**
 * API service layer for the FastAPI backend.
 *
 * Every network call the app makes goes through this file — components
 * never call fetch() directly. This keeps the backend contract (URLs,
 * request shape, error parsing) in one place.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Error type thrown by this module so components can distinguish
 * "backend responded with an error" from "network/unexpected error"
 * and show an appropriate message.
 */
export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * Uploads a PDF to POST /extract and returns the parsed extraction
 * result: { job_id, filename, total_pages, tables_by_page }.
 */
export async function extractTables(file) {
  const formData = new FormData()
  formData.append('file', file)

  let response
  try {
    response = await fetch(`${API_BASE_URL}/extract`, {
      method: 'POST',
      body: formData,
    })
  } catch (networkError) {
    throw new ApiError(
      'Could not reach the extraction server. Confirm the backend is running and try again.',
      0,
    )
  }

  if (!response.ok) {
    let detail = `Extraction failed (HTTP ${response.status}).`
    try {
      const body = await response.json()
      if (body?.detail) detail = body.detail
    } catch {
      // response wasn't JSON — keep the generic message
    }
    throw new ApiError(detail, response.status)
  }

  return response.json()
}

/**
 * Returns the absolute download URL for a completed job's JSON result.
 * Used directly as an <a href> so the browser handles the download.
 */
export function getDownloadUrl(jobId) {
  return `${API_BASE_URL}/download/${jobId}`
}

/**
 * Builds an absolute URL for a detected stamp/signature crop from the
 * relative path the backend returns (e.g.
 * "/crops/{job_id}/page_1_stamp_1.png"). Reuses the same API_BASE_URL
 * as every other call in this file — the job ID and filename always
 * come from the API response, never hardcoded here.
 */
export function getCropUrl(relativeImageUrl) {
  return `${API_BASE_URL}${relativeImageUrl}`
}
