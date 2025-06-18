import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryInput } from '../QueryInput'
import { useAppStore } from '../../store/useAppStore'

// Mock the store
vi.mock('../../store/useAppStore')

describe('QueryInput', () => {
  const mockOnSubmit = vi.fn()
  const mockSetCurrentQuery = vi.fn()
  const mockSetMaxConversations = vi.fn()

  const defaultStoreValues = {
    currentQuery: '',
    isLoading: false,
    maxConversations: 50,
    setCurrentQuery: mockSetCurrentQuery,
    setMaxConversations: mockSetMaxConversations,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    ;(useAppStore as any).mockReturnValue(defaultStoreValues)
  })

  it('renders query input form', () => {
    render(<QueryInput onSubmit={mockOnSubmit} />)
    
    expect(screen.getByLabelText(/Ask about your Intercom conversations/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Analyze' })).toBeInTheDocument()
  })

  it('displays example queries', () => {
    render(<QueryInput onSubmit={mockOnSubmit} />)
    
    expect(screen.getByText('Try these examples:')).toBeInTheDocument()
    expect(screen.getByText(/What are the top customer complaints this month/)).toBeInTheDocument()
    expect(screen.getByText(/Show me product feedback from the last week/)).toBeInTheDocument()
  })

  it('submits query when form is submitted', async () => {
    const user = userEvent.setup()
    render(<QueryInput onSubmit={mockOnSubmit} />)
    
    const textarea = screen.getByLabelText(/Ask about your Intercom conversations/)
    const submitButton = screen.getByRole('button', { name: 'Analyze' })
    
    await user.type(textarea, 'Test query')
    await user.click(submitButton)
    
    expect(mockOnSubmit).toHaveBeenCalledWith('Test query')
    expect(mockSetCurrentQuery).toHaveBeenCalledWith('Test query')
  })

  it('prevents submission with empty query', async () => {
    const user = userEvent.setup()
    render(<QueryInput onSubmit={mockOnSubmit} />)
    
    const submitButton = screen.getByRole('button', { name: 'Analyze' })
    await user.click(submitButton)
    
    expect(mockOnSubmit).not.toHaveBeenCalled()
  })

  it('shows loading state when isLoading is true', () => {
    ;(useAppStore as any).mockReturnValue({
      ...defaultStoreValues,
      isLoading: true,
    })

    render(<QueryInput onSubmit={mockOnSubmit} />)
    
    expect(screen.getByText('Analyzing...')).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('updates max conversations value', async () => {
    const user = userEvent.setup()
    render(<QueryInput onSubmit={mockOnSubmit} />)
    
    const input = screen.getByLabelText(/Max conversations:/)
    await user.clear(input)
    await user.type(input, '100')
    
    expect(mockSetMaxConversations).toHaveBeenCalledWith(100)
  })

  it('handles example query clicks', async () => {
    const user = userEvent.setup()
    render(<QueryInput onSubmit={mockOnSubmit} />)
    
    const exampleButton = screen.getByText(/What are the top customer complaints this month/)
    await user.click(exampleButton)
    
    expect(mockSetCurrentQuery).toHaveBeenCalledWith(
      'What are the top customer complaints this month?'
    )
  })

  it('disables controls when loading', () => {
    ;(useAppStore as any).mockReturnValue({
      ...defaultStoreValues,
      isLoading: true,
    })

    render(<QueryInput onSubmit={mockOnSubmit} />)
    
    const textarea = screen.getByLabelText(/Ask about your Intercom conversations/)
    const maxConversationsInput = screen.getByLabelText(/Max conversations:/)
    const exampleButtons = screen.getAllByRole('button').filter(
      button => button.textContent?.includes('complaint') || 
                button.textContent?.includes('feedback')
    )
    
    expect(textarea).toBeDisabled()
    expect(maxConversationsInput).toBeDisabled()
    exampleButtons.forEach(button => expect(button).toBeDisabled())
  })

  it('prevents submission during loading', async () => {
    ;(useAppStore as any).mockReturnValue({
      ...defaultStoreValues,
      currentQuery: 'Test query',
      isLoading: true,
    })

    const user = userEvent.setup()
    render(<QueryInput onSubmit={mockOnSubmit} />)
    
    const form = screen.getByRole('button', { name: /Analyzing/ }).closest('form')
    if (form) {
      fireEvent.submit(form)
    }
    
    expect(mockOnSubmit).not.toHaveBeenCalled()
  })
})
