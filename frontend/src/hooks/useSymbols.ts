import { useQuery } from '@tanstack/react-query'
import { getSymbols } from '../services/api'

export function useSymbols() {
  return useQuery({ queryKey: ['symbols'], queryFn: getSymbols })
}
