import { useEffect, useState } from 'react'
import { Subject, subjectApi } from '../api/subject'
import { enrollmentApi, EnrollmentListItem } from '../api/enrollment'
import { useAuthStore } from '../stores/useAuthStore'

/**
 * Hook: provides subject list with optional "only my enrolled subjects" filter.
 *
 * When `onlyEnrolled` is true and the user is logged in, the hook loads
 * the user's enrollments, fetches each enrollment's subjects, deduplicates
 * by subject code, and returns only those subjects (intersected with the
 * full subject list to keep question_count etc.).
 *
 * Usage:
 *   const { subjects, onlyEnrolled, setOnlyEnrolled, loading } = useEnrolledSubjectFilter(hasContentOnly)
 */
export function useEnrolledSubjectFilter(hasContentOnly?: boolean) {
  const user = useAuthStore((s) => s.user)
  const [allSubjects, setAllSubjects] = useState<Subject[]>([])
  const [enrolledCodes, setEnrolledCodes] = useState<Set<string> | null>(null)
  const [onlyEnrolled, setOnlyEnrolled] = useState(false)
  const [loading, setLoading] = useState(true)

  // Load all subjects
  useEffect(() => {
    subjectApi
      .list(undefined, hasContentOnly)
      .then(setAllSubjects)
      .catch(() => setAllSubjects([]))
      .finally(() => setLoading(false))
  }, [hasContentOnly])

  // Load enrolled subject codes when user is logged in
  useEffect(() => {
    if (!user) {
      setEnrolledCodes(null)
      return
    }
    enrollmentApi
      .listEnrollments()
      .then(async (enrollments: EnrollmentListItem[]) => {
        if (enrollments.length === 0) {
          setEnrolledCodes(new Set())
          return
        }
        // Load subjects from all enrollments
        const results = await Promise.all(
          enrollments.map((e) => enrollmentApi.getEnrollmentSubjects(e.id).catch(() => null)),
        )
        const codes = new Set<string>()
        for (const data of results) {
          if (!data) continue
          for (const group of [data.subjects.required, data.subjects.elective, data.subjects.additional]) {
            for (const s of group) {
              codes.add(s.code)
            }
          }
        }
        setEnrolledCodes(codes)
      })
      .catch(() => setEnrolledCodes(null))
  }, [user])

  // Compute filtered list
  const subjects =
    onlyEnrolled && enrolledCodes
      ? allSubjects.filter((s) => enrolledCodes.has(s.code))
      : allSubjects

  return {
    /** Filtered subject list (all or enrolled-only) */
    subjects,
    /** All subjects without filter */
    allSubjects,
    /** Whether "only enrolled" filter is active */
    onlyEnrolled,
    /** Toggle the filter */
    setOnlyEnrolled,
    /** Whether data is still loading */
    loading,
    /** Whether user has enrollments (null = not logged in) */
    hasEnrollments: enrolledCodes !== null && enrolledCodes.size > 0,
    /** Whether user is logged in */
    isLoggedIn: !!user,
  }
}
