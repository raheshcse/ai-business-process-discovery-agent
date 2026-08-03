import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/Button'
import { InlineError } from '@/components/ui/States'
import { cn } from '@/lib/cn'
import { PROJECT_STATUSES } from '@/types/api'
import type { Project, ProjectCreate } from '@/types/api'

export interface ProjectFormErrors {
  name?: string
  objective?: string
  client_name?: string
  department?: string
  industry?: string
}

/** Limits mirror the `max_length` constraints on the Pydantic schema, so
 *  the form rejects what the API would reject, before the round trip. */
export function validateProject(values: ProjectCreate): ProjectFormErrors {
  const errors: ProjectFormErrors = {}
  const name = values.name.trim()
  const objective = values.objective.trim()

  if (!name) errors.name = 'Give the project a name.'
  else if (name.length > 200) errors.name = 'Keep the name under 200 characters.'

  if (!objective) errors.objective = 'Describe what you want to discover.'
  else if (objective.length < 10)
    errors.objective = 'Add a little more detail — at least 10 characters.'

  if ((values.client_name ?? '').length > 200)
    errors.client_name = 'Keep this under 200 characters.'
  if ((values.department ?? '').length > 200)
    errors.department = 'Keep this under 200 characters.'
  if ((values.industry ?? '').length > 100)
    errors.industry = 'Keep this under 100 characters.'

  return errors
}

const EMPTY: ProjectCreate = {
  name: '',
  client_name: '',
  department: '',
  industry: '',
  objective: '',
  status: 'draft',
}

export function ProjectForm({
  project,
  submitLabel,
  submitting,
  onSubmit,
  onCancel,
  formId,
}: {
  project?: Project
  submitLabel: string
  submitting: boolean
  onSubmit: (values: ProjectCreate) => void
  onCancel: () => void
  formId: string
}) {
  const [values, setValues] = useState<ProjectCreate>(
    project
      ? {
          name: project.name,
          client_name: project.client_name ?? '',
          department: project.department ?? '',
          industry: project.industry ?? '',
          objective: project.objective,
          status: project.status,
        }
      : EMPTY,
  )
  const [errors, setErrors] = useState<ProjectFormErrors>({})
  const [touched, setTouched] = useState(false)

  const update = (field: keyof ProjectCreate, value: string) => {
    const next = { ...values, [field]: value }
    setValues(next)
    if (touched) setErrors(validateProject(next))
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    setTouched(true)
    const found = validateProject(values)
    setErrors(found)
    if (Object.keys(found).length > 0) return

    onSubmit({
      name: values.name.trim(),
      objective: values.objective.trim(),
      // Empty optional strings become null so the API stores absence, not "".
      client_name: values.client_name?.trim() || null,
      department: values.department?.trim() || null,
      industry: values.industry?.trim() || null,
      status: values.status,
    })
  }

  return (
    <form id={formId} onSubmit={handleSubmit} noValidate className="space-y-4">
      <Field
        id="name"
        label="Project name"
        required
        value={values.name}
        error={errors.name}
        onChange={(value) => update('name', value)}
        placeholder="Accounts payable review"
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field
          id="client_name"
          label="Client"
          value={values.client_name ?? ''}
          error={errors.client_name}
          onChange={(value) => update('client_name', value)}
          placeholder="Northwind Ltd"
        />
        <Field
          id="department"
          label="Department"
          value={values.department ?? ''}
          error={errors.department}
          onChange={(value) => update('department', value)}
          placeholder="Finance"
        />
        <Field
          id="industry"
          label="Industry"
          value={values.industry ?? ''}
          error={errors.industry}
          onChange={(value) => update('industry', value)}
          placeholder="Manufacturing"
        />
        <div>
          <label className="label" htmlFor="status">
            Status
          </label>
          <select
            id="status"
            className="input mt-1.5"
            value={values.status}
            onChange={(event) => update('status', event.target.value)}
          >
            {PROJECT_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="label" htmlFor="objective">
          Objective <span className="text-red-600">*</span>
        </label>
        <textarea
          id="objective"
          rows={3}
          className={cn('input mt-1.5 resize-y', errors.objective && 'input-invalid')}
          value={values.objective}
          onChange={(event) => update('objective', event.target.value)}
          placeholder="Understand how invoices are approved today and where the process slows down."
          aria-invalid={Boolean(errors.objective)}
          aria-describedby={errors.objective ? 'objective-error' : undefined}
        />
        {errors.objective ? (
          <span id="objective-error">
            <InlineError>{errors.objective}</InlineError>
          </span>
        ) : null}
      </div>

      <div className="flex justify-end gap-2 pt-1">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={submitting}>
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}

function Field({
  id,
  label,
  value,
  error,
  onChange,
  placeholder,
  required,
}: {
  id: string
  label: string
  value: string
  error?: string
  onChange: (value: string) => void
  placeholder?: string
  required?: boolean
}) {
  return (
    <div>
      <label className="label" htmlFor={id}>
        {label}
        {required ? <span className="text-red-600"> *</span> : null}
      </label>
      <input
        id={id}
        className={cn('input mt-1.5', error && 'input-invalid')}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : undefined}
      />
      {error ? (
        <span id={`${id}-error`}>
          <InlineError>{error}</InlineError>
        </span>
      ) : null}
    </div>
  )
}
