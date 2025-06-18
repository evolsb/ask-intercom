import { render, screen, fireEvent } from '@testing-library/react'
import { ApiKeySetup } from '../ApiKeySetup'
import { useAppStore } from '../../store/useAppStore'

// Mock the store
vi.mock('../../store/useAppStore')

describe('ApiKeySetup', () => {
  const mockSetIntercomToken = vi.fn()
  const mockSetOpenaiKey = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    ;(useAppStore as any).mockReturnValue({
      intercomToken: '',
      openaiKey: '',
      setIntercomToken: mockSetIntercomToken,
      setOpenaiKey: mockSetOpenaiKey,
    })
  })

  it('renders API configuration form', () => {
    render(<ApiKeySetup />)
    
    expect(screen.getByText('API Configuration')).toBeInTheDocument()
    expect(screen.getByLabelText('Intercom Access Token')).toBeInTheDocument()
    expect(screen.getByLabelText('OpenAI API Key')).toBeInTheDocument()
  })

  it('shows red indicator when not configured', () => {
    render(<ApiKeySetup />)
    
    const indicator = document.querySelector('.bg-red-500')
    expect(indicator).toBeInTheDocument()
  })

  it('shows green indicator when both keys are configured', () => {
    ;(useAppStore as any).mockReturnValue({
      intercomToken: 'test-intercom-token',
      openaiKey: 'sk-test-openai-key',
      setIntercomToken: mockSetIntercomToken,
      setOpenaiKey: mockSetOpenaiKey,
    })

    render(<ApiKeySetup />)
    
    const indicator = document.querySelector('.bg-green-500')
    expect(indicator).toBeInTheDocument()
  })

  it('updates intercom token when input changes', () => {
    render(<ApiKeySetup />)
    
    const input = screen.getByLabelText('Intercom Access Token')
    fireEvent.change(input, { target: { value: 'new-token' } })
    
    expect(mockSetIntercomToken).toHaveBeenCalledWith('new-token')
  })

  it('updates openai key when input changes', () => {
    render(<ApiKeySetup />)
    
    const input = screen.getByLabelText('OpenAI API Key')
    fireEvent.change(input, { target: { value: 'sk-new-key' } })
    
    expect(mockSetOpenaiKey).toHaveBeenCalledWith('sk-new-key')
  })

  it('toggles password visibility', () => {
    ;(useAppStore as any).mockReturnValue({
      intercomToken: 'test-token',
      openaiKey: 'sk-test-key',
      setIntercomToken: mockSetIntercomToken,
      setOpenaiKey: mockSetOpenaiKey,
    })

    render(<ApiKeySetup />)
    
    const checkbox = screen.getByLabelText('Show API keys')
    const intercomInput = screen.getByLabelText('Intercom Access Token')
    const openaiInput = screen.getByLabelText('OpenAI API Key')
    
    // Initially password type
    expect(intercomInput).toHaveAttribute('type', 'password')
    expect(openaiInput).toHaveAttribute('type', 'password')
    
    // Toggle to text type
    fireEvent.click(checkbox)
    expect(intercomInput).toHaveAttribute('type', 'text')
    expect(openaiInput).toHaveAttribute('type', 'text')
  })

  it('displays privacy information', () => {
    render(<ApiKeySetup />)
    
    expect(screen.getByText(/Keys are stored locally in your browser/)).toBeInTheDocument()
    expect(screen.getByText(/Data is automatically deleted after 30 days/)).toBeInTheDocument()
    expect(screen.getByText(/Never share your API keys with others/)).toBeInTheDocument()
  })
})
