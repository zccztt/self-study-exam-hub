import { useEffect } from 'react'

const optionLetters = ['A', 'B', 'C', 'D', 'E', 'F']

interface UseExamHotkeysOptions {
  /** Whether hotkeys are active (exam in progress, no score result) */
  active: boolean
  /** Current list of questions */
  questions: { id: number; question_type: string; options: string[] }[]
  /** Current question index being viewed (for scroll position detection) */
  currentQuestionId: number | null
  /** Callback to set answer for single choice */
  onSingleAnswer: (questionId: number, letter: string) => void
  /** Callback to toggle answer for multiple choice */
  onMultipleToggle: (questionId: number, letter: string) => void
  /** Callback to navigate to next question */
  onNextQuestion: () => void
  /** Callback to navigate to previous question */
  onPrevQuestion: () => void
  /** Callback to flag current question */
  onFlagQuestion: () => void
}

/**
 * Provides keyboard shortcuts during exam answering:
 * - 1-6 / A-F: Select option for single/multiple choice
 * - Enter / ArrowDown: Next question
 * - ArrowUp: Previous question
 * - Space: Flag/unflag current question
 */
export function useExamHotkeys({
  active,
  questions,
  currentQuestionId,
  onSingleAnswer,
  onMultipleToggle,
  onNextQuestion,
  onPrevQuestion,
  onFlagQuestion,
}: UseExamHotkeysOptions) {
  useEffect(() => {
    if (!active) return

    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't capture when typing in input/textarea
      const target = event.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') {
        return
      }

      const currentQuestion = questions.find((q) => q.id === currentQuestionId)
      if (!currentQuestion) return

      // Number keys 1-6 => select option
      const numKey = parseInt(event.key, 10)
      if (numKey >= 1 && numKey <= 6 && numKey <= currentQuestion.options.length) {
        event.preventDefault()
        const letter = optionLetters[numKey - 1]
        if (currentQuestion.question_type === 'single_choice') {
          onSingleAnswer(currentQuestion.id, letter)
        } else if (currentQuestion.question_type === 'multiple_choice') {
          onMultipleToggle(currentQuestion.id, letter)
        }
        return
      }

      // Letter keys A-F => select option
      const letterKey = event.key.toUpperCase()
      const letterIndex = optionLetters.indexOf(letterKey)
      if (letterIndex >= 0 && letterIndex < currentQuestion.options.length) {
        event.preventDefault()
        if (currentQuestion.question_type === 'single_choice') {
          onSingleAnswer(currentQuestion.id, letterKey)
        } else if (currentQuestion.question_type === 'multiple_choice') {
          onMultipleToggle(currentQuestion.id, letterKey)
        }
        return
      }

      // Navigation
      if (event.key === 'ArrowDown' || (event.key === 'Enter' && !event.shiftKey)) {
        event.preventDefault()
        onNextQuestion()
        return
      }

      if (event.key === 'ArrowUp') {
        event.preventDefault()
        onPrevQuestion()
        return
      }

      // Space => flag
      if (event.key === ' ') {
        event.preventDefault()
        onFlagQuestion()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [active, questions, currentQuestionId, onSingleAnswer, onMultipleToggle, onNextQuestion, onPrevQuestion, onFlagQuestion])
}
