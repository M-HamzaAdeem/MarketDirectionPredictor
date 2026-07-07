import { useQuery } from '@tanstack/react-query'
import { getConfig } from '../services/api'

export function useConfig() {
  return useQuery({ queryKey: ['config'], queryFn: getConfig })
}
