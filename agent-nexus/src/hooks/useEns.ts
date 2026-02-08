import { useEnsName, useEnsAvatar, useEnsAddress, useEnsText } from 'wagmi'

/**
 * Custom hook to fetch ENS profile data (name and avatar) for a given address.
 * ENS resolution always uses Ethereum mainnet (chainId: 1).
 */
export function useEnsProfile(address?: `0x${string}`) {
  const { data: ensName, isLoading: nameLoading, isError: nameError } = useEnsName({ 
    address, 
    chainId: 1 
  })
  
  const { data: ensAvatar, isLoading: avatarLoading, isError: avatarError } = useEnsAvatar({ 
    name: ensName ?? undefined, 
    chainId: 1 
  })
  
  return { 
    ensName, 
    ensAvatar, 
    isLoading: nameLoading || avatarLoading,
    isError: nameError || avatarError
  }
}

/**
 * Custom hook to resolve an ENS name to an Ethereum address.
 * Only enables the query if the name contains '.eth'.
 */
export function useEnsResolver(ensName?: string) {
  const { data: address, isLoading, isError } = useEnsAddress({ 
    name: ensName, 
    chainId: 1,
    query: { enabled: !!ensName && ensName.includes('.eth') }
  })
  
  return { address, isLoading, isError }
}

/**
 * Custom hook to fetch a specific ENS text record for a name.
 * Common keys: 'description', 'url', 'com.twitter', 'com.github', 'email'
 */
export function useEnsTextRecord(ensName?: string, key?: string) {
  const { data: value, isLoading, isError } = useEnsText({
    name: ensName,
    key,
    chainId: 1,
    query: { enabled: !!ensName && !!key }
  })
  
  return { value, isLoading, isError }
}
