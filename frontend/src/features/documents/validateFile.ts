import { ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_BYTES } from '@/api/config'
import { formatBytes } from '@/lib/format'

/**
 * Client-side mirror of `DocumentService.upload_document`'s rules.
 *
 * The server validates all of this again -- this only exists so a user
 * learns a 30 MB file is too large before waiting for it to upload.
 */
export function validateFile(file: File): string | null {
  const name = file.name.replace(/\\/g, '/').split('/').pop() ?? ''
  const dot = name.lastIndexOf('.')
  const extension = dot === -1 ? '' : name.slice(dot).toLowerCase()

  if (!name || dot === 0 || !extension) {
    return 'That file has no name or extension.'
  }
  if (!(ALLOWED_EXTENSIONS as readonly string[]).includes(extension)) {
    return `${extension} files are not supported. Upload ${ALLOWED_EXTENSIONS.join(', ')}.`
  }
  if (name.length > 255) {
    return 'That filename is longer than 255 characters.'
  }
  if (file.size === 0) {
    return 'That file is empty.'
  }
  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    return `That file is ${formatBytes(file.size)}. The limit is ${formatBytes(MAX_UPLOAD_SIZE_BYTES)}.`
  }
  return null
}
