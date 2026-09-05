import React from 'react'

interface Props {
  onlyEnrolled: boolean
  setOnlyEnrolled: (v: boolean) => void
  hasEnrollments: boolean
  isLoggedIn: boolean
}

/**
 * Toggle switch: "只看报考科目"
 * Only renders when user is logged in and has enrollments.
 */
const EnrolledSubjectToggle: React.FC<Props> = ({ onlyEnrolled, setOnlyEnrolled, hasEnrollments, isLoggedIn }) => {
  if (!isLoggedIn || !hasEnrollments) return null

  return (
    <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm transition hover:border-blue-300">
      <div
        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
          onlyEnrolled ? 'bg-blue-600' : 'bg-slate-300'
        }`}
        onClick={() => setOnlyEnrolled(!onlyEnrolled)}
      >
        <span
          className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
            onlyEnrolled ? 'translate-x-4' : 'translate-x-0.5'
          }`}
        />
      </div>
      <span className={`font-medium ${onlyEnrolled ? 'text-blue-700' : 'text-slate-600'}`}>
        只看报考科目
      </span>
    </label>
  )
}

export default EnrolledSubjectToggle
