import { render, screen } from '@testing-library/react'
import { ResultsDisplay } from '../ResultsDisplay'
import { useAppStore } from '../../store/useAppStore'

// Mock the store
vi.mock('../../store/useAppStore')

describe('ResultsDisplay', () => {
  const mockResult = {
    insights: [
      'Top complaint: Slow response times mentioned 15 times',
      'Feature request: Dark mode requested by 8 customers',
      'Bug report: Login issues affecting mobile users'
    ],
    cost: 0.25,
    response_time_ms: 12500,
    conversation_count: 42
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows empty state when no result', () => {
    ;(useAppStore as any).mockReturnValue({
      lastResult: null,
      error: null,
      isLoading: false,
      currentQuery: '',
    })

    render(<ResultsDisplay />)
    
    expect(screen.getByText('Ready to analyze')).toBeInTheDocument()
    expect(screen.getByText(/Configure your API keys and enter a query/)).toBeInTheDocument()
  })

  it('shows loading state', () => {
    ;(useAppStore as any).mockReturnValue({
      lastResult: null,
      error: null,
      isLoading: true,
      currentQuery: 'Test query',
    })

    render(<ResultsDisplay />)
    
    expect(screen.getByText('Analyzing conversations...')).toBeInTheDocument()
    expect(screen.getByText('Processing: "Test query"')).toBeInTheDocument()
    expect(screen.getByText(/Fetching conversations from Intercom/)).toBeInTheDocument()
  })

  it('shows error state', () => {
    ;(useAppStore as any).mockReturnValue({
      lastResult: null,
      error: 'API key validation failed',
      isLoading: false,
      currentQuery: '',
    })

    render(<ResultsDisplay />)
    
    expect(screen.getByText('Analysis Failed')).toBeInTheDocument()
    expect(screen.getByText('API key validation failed')).toBeInTheDocument()
    expect(screen.getByText('Troubleshooting tips')).toBeInTheDocument()
  })

  it('displays analysis results', () => {
    ;(useAppStore as any).mockReturnValue({
      lastResult: mockResult,
      error: null,
      isLoading: false,
      currentQuery: '',
    })

    render(<ResultsDisplay />)
    
    expect(screen.getByText('Analysis Results')).toBeInTheDocument()
    expect(screen.getByText(/Slow response times mentioned 15 times/)).toBeInTheDocument()
    expect(screen.getByText(/Dark mode requested by 8 customers/)).toBeInTheDocument()
    expect(screen.getByText(/Login issues affecting mobile users/)).toBeInTheDocument()
  })

  it('displays metrics correctly', () => {
    ;(useAppStore as any).mockReturnValue({
      lastResult: mockResult,
      error: null,
      isLoading: false,
      currentQuery: '',
    })

    render(<ResultsDisplay />)
    
    expect(screen.getByText('42 conversations')).toBeInTheDocument()
    expect(screen.getByText('12.5s')).toBeInTheDocument()
    expect(screen.getByText('$0.250')).toBeInTheDocument()
  })

  it('formats currency correctly', () => {
    const result = { ...mockResult, cost: 1.234 }
    ;(useAppStore as any).mockReturnValue({
      lastResult: result,
      error: null,
      isLoading: false,
      currentQuery: '',
    })

    render(<ResultsDisplay />)
    
    expect(screen.getByText('$1.234')).toBeInTheDocument()
  })

  it('formats duration correctly for milliseconds', () => {
    const result = { ...mockResult, response_time_ms: 500 }
    ;(useAppStore as any).mockReturnValue({
      lastResult: result,
      error: null,
      isLoading: false,
      currentQuery: '',
    })

    render(<ResultsDisplay />)
    
    expect(screen.getByText('500ms')).toBeInTheDocument()
  })

  it('formats duration correctly for minutes', () => {
    const result = { ...mockResult, response_time_ms: 125000 } // 2+ minutes
    ;(useAppStore as any).mockReturnValue({
      lastResult: result,
      error: null,
      isLoading: false,
      currentQuery: '',
    })

    render(<ResultsDisplay />)
    
    expect(screen.getByText('2.1m')).toBeInTheDocument()
  })

  it('numbers insights correctly', () => {
    ;(useAppStore as any).mockReturnValue({
      lastResult: mockResult,
      error: null,
      isLoading: false,
      currentQuery: '',
    })

    render(<ResultsDisplay />)
    
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('shows loading progress steps', () => {
    ;(useAppStore as any).mockReturnValue({
      lastResult: null,
      error: null,
      isLoading: true,
      currentQuery: 'Test query',
    })

    render(<ResultsDisplay />)
    
    expect(screen.getByText(/Fetching conversations from Intercom/)).toBeInTheDocument()
    expect(screen.getByText(/Analyzing with AI/)).toBeInTheDocument()
    expect(screen.getByText(/Generating insights/)).toBeInTheDocument()
    expect(screen.getByText(/This usually takes 10-30 seconds/)).toBeInTheDocument()
  })
})
