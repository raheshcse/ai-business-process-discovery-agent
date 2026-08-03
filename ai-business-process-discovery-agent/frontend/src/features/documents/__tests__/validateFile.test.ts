import { describe, expect, it } from 'vitest'
import { validateFile } from '../validateFile'

const makeFile = (name: string, size: number, type = 'text/plain') => {
  const file = new File(['x'], name, { type })
  Object.defineProperty(file, 'size', { value: size })
  return file
}

describe('validateFile', () => {
  it('accepts every extension the backend allows', () => {
    for (const extension of ['pdf', 'docx', 'txt', 'csv', 'xlsx']) {
      expect(validateFile(makeFile(`process.${extension}`, 1024))).toBeNull()
    }
  })

  it('accepts an uppercase extension', () => {
    expect(validateFile(makeFile('PROCESS.PDF', 1024))).toBeNull()
  })

  it('rejects an unsupported type', () => {
    expect(validateFile(makeFile('notes.exe', 1024))).toMatch(/not supported/)
  })

  it('rejects a file with no extension', () => {
    expect(validateFile(makeFile('README', 1024))).toMatch(/no name or extension/)
  })

  it('rejects an empty file', () => {
    expect(validateFile(makeFile('empty.txt', 0))).toMatch(/empty/)
  })

  it('rejects a file over the 25 MB limit', () => {
    const message = validateFile(makeFile('huge.pdf', 26 * 1024 * 1024))
    expect(message).toMatch(/limit is 25 MB/)
  })

  it('accepts a file exactly at the limit', () => {
    expect(validateFile(makeFile('exact.pdf', 25 * 1024 * 1024))).toBeNull()
  })

  it('rejects a filename over 255 characters', () => {
    const long = `${'a'.repeat(260)}.txt`
    expect(validateFile(makeFile(long, 1024))).toMatch(/255 characters/)
  })

  it('handles a Windows path the way the backend does', () => {
    expect(validateFile(makeFile('C:\\Users\\me\\process.pdf', 1024))).toBeNull()
  })
})
