import { useEffect, useRef, type ReactNode } from 'react'

/**
 * Dialog with focus containment and Escape-to-close. Built on `<dialog>`
 * so the browser handles the top layer and the accessibility semantics
 * rather than us reimplementing them.
 */
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
}: {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  children: ReactNode
  footer?: ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    const handleCancel = (event: Event) => {
      event.preventDefault()
      onClose()
    }
    dialog.addEventListener('cancel', handleCancel)
    return () => dialog.removeEventListener('cancel', handleCancel)
  }, [onClose])

  if (!open) return null

  return (
    <dialog
      ref={ref}
      aria-labelledby="modal-title"
      className="w-[min(36rem,calc(100vw-2rem))] rounded-xl p-0 shadow-raised backdrop:bg-navy-950/50"
      onClick={(event) => {
        if (event.target === ref.current) onClose()
      }}
    >
      <div className="border-b border-navy-100 px-6 py-4">
        <h2 id="modal-title" className="text-base font-semibold text-navy-900">
          {title}
        </h2>
        {description ? (
          <p className="mt-1 text-sm text-navy-500">{description}</p>
        ) : null}
      </div>
      <div className="max-h-[60vh] overflow-y-auto px-6 py-5">{children}</div>
      {footer ? (
        <div className="flex justify-end gap-2 border-t border-navy-100 bg-navy-50/60 px-6 py-4">
          {footer}
        </div>
      ) : null}
    </dialog>
  )
}
