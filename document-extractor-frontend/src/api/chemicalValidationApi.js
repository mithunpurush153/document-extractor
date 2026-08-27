const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export class ChemicalValidationApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ChemicalValidationApiError'
    this.status = status
  }
}

export async function validateChemicalDocuments(referencePdf, testPdf) {
  const formData = new FormData()
  formData.append('reference_pdf', referencePdf)
  formData.append('test_pdf', testPdf)

  let response
  try {
    response = await fetch(`${API_BASE_URL}/chemical/validate`, {
      method: 'POST',
      body: formData,
    })
  } catch {
    throw new ChemicalValidationApiError(
      'Could not reach the validation server. Confirm the backend is running and try again.',
      0,
    )
  }

  if (!response.ok) {
    let detail = `Validation failed (HTTP ${response.status}).`
    try {
      const body = await response.json()
      if (body?.detail) detail = body.detail
    } catch {
      // Keep generic message if response is not JSON.
    }
    throw new ChemicalValidationApiError(detail, response.status)
  }

  return response.json()
}
